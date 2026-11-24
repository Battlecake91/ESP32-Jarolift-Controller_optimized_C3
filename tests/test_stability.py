"""Exercise actual MQTT packet methods and log-ring code without ESP hardware."""
from pathlib import Path
import subprocess
import tempfile
from host_helpers import ROOT

LIB = ROOT / "lib/async-mqtt-client/src"

def extract(source, signature):
    start = source.index(signature)
    end = source.index("\n}", start) + 2
    return source[start:end]

def main():
    mqtt = (LIB / "AsyncMqttClient.cpp").read_text()
    packet = (LIB / "AsyncMqttClient/Packets/Out/OutPacket.cpp").read_text()
    msg = (ROOT / "src/message.cpp").read_text()
    code = r"""
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstddef>
#include <mutex>

#define GET_FREE_MEMORY() 100000
#define MQTT_MIN_FREE_MEMORY 4096
#define log_i(...) ((void)0)
namespace AsyncMqttClientInternals {
namespace PacketType { constexpr uint8_t PUBLISH = 3; }
struct Packet {
    uint16_t id;
    bool released = false;
    uint16_t packetId() const { assert(!released); return id; }
};
struct SubscribeOutPacket : Packet {
    SubscribeOutPacket(const char*, uint8_t) { id = 10; }
};
struct UnsubscribeOutPacket : Packet {
    UnsubscribeOutPacket(const char*) { id = 20; }
};
struct PublishOutPacket : Packet {
    PublishOutPacket(const char*, uint8_t, bool, const char*, size_t) { id = 30; }
};
struct OutPacket {
    uint8_t bytes[2]{};
    const uint8_t* data() const { return bytes; }
    uint8_t packetType() const { return bytes[0] >> 4; }
    uint8_t qos() const;
};
}
using AsyncMqttClientInternals::OutPacket;
class AsyncMqttClient {
    enum { DISCONNECTED, CONNECTED } _state = CONNECTED;
    AsyncMqttClientInternals::Packet* last = nullptr;
    template<class T> void _addBack(T* p) {
        // Model synchronous ownership transfer without dereferencing freed memory.
        p->released = true;
        last = p;
    }
public:
    uint16_t subscribe(const char*, uint8_t);
    uint16_t unsubscribe(const char*);
    uint16_t publish(const char*, uint8_t, bool, const char*, size_t, bool, uint16_t);
    void forget() { last = nullptr; }
};
constexpr size_t MAX_LOG_LINES = 4, MAX_LOG_ENTRY = 128;
struct LogSnapshot { uint64_t end; size_t count; };
using portMUX_TYPE = std::mutex;
#define portMUX_INITIALIZER_UNLOCKED {}
#define portENTER_CRITICAL(m) ((m)->lock())
#define portEXIT_CRITICAL(m) ((m)->unlock())
namespace EspStrUtil { const char* getDateTimeString() { return "T"; } }
"""
    # In the mock, ownership transfer invalidates the object immediately.
    # Keep it alive solely so an old packetId() read deterministically asserts.
    code += "\n".join(extract(mqtt, "uint16_t AsyncMqttClient::" + name + "(")
                      for name in ("subscribe", "unsubscribe", "publish"))
    code += "\n" + extract(packet, "uint8_t OutPacket::qos()")
    start = msg.index("static char logBuffer[")
    end = msg.index("esp_log_level_t logLevel", start)
    code += "\n" + msg[start:end]
    code += "\n" + extract(msg, "void clearLogBuffer()")
    code += "\n" + extract(msg, "void addLogBuffer(")
    code += r"""
int main() {
    AsyncMqttClient mqtt;
    assert(mqtt.subscribe("x", 0) == 10);
    assert(mqtt.unsubscribe("x") == 20);
    assert(mqtt.publish("x", 0, false, "y", 1, false, 0) == 30);
    OutPacket p;
    for (unsigned qos = 0; qos < 3; ++qos) {
        for (unsigned length = 0; length < 128; ++length) {
            p.bytes[0] = 0x30 | (qos << 1);
            p.bytes[1] = length;
            assert(p.qos() == qos);
        }
    }
    clearLogBuffer();
    assert(logSnapshot().count == 0);
    char entry[MAX_LOG_ENTRY];
    addLogBuffer("A"); addLogBuffer("B"); addLogBuffer("C"); addLogBuffer("D");
    auto full = logSnapshot();
    assert(full.count == 4);
    assert(readLogEntry(full, 0, false, entry) && strstr(entry, "A"));
    assert(readLogEntry(full, 0, true, entry) && strstr(entry, "D"));
    addLogBuffer("E");
    assert(!readLogEntry(full, 0, false, entry));
    assert(readLogEntry(full, 1, false, entry) && strstr(entry, "B"));
    auto wrapped = logSnapshot();
    assert(wrapped.count == 4);
    assert(readLogEntry(wrapped, 0, false, entry) && strstr(entry, "B"));
    clearLogBuffer();
    addLogBuffer("F");
    assert(!readLogEntry(wrapped, 3, false, entry));
    assert(logSnapshot().count == 1);
    assert(readLogEntry(logSnapshot(), 0, false, entry) && strstr(entry, "F"));
}
"""
    with tempfile.TemporaryDirectory(prefix="jarolift-stability-") as directory:
        source = Path(directory) / "test.cpp"
        binary = source.with_suffix("")
        source.write_text(code)
        subprocess.run(["c++", "-std=c++17", "-pthread", str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print("PASS: MQTT packet ownership/QoS and log ring wrap/clear/snapshot behavior.")

if __name__ == "__main__":
    main()
