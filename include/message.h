#pragma once
#include <Arduino.h>

/* D E C L A R A T I O N S ****************************************************/

// ESP32-S2 shares its limited internal RAM between instruction and data sections.
// Keep the log bounded without reducing positioning or remote-mapping capacity.
#if defined(CONFIG_IDF_TARGET_ESP32C3) && CONFIG_IDF_TARGET_ESP32C3
#define MAX_LOG_LINES 64
#elif defined(CONFIG_IDF_TARGET_ESP32S2) && CONFIG_IDF_TARGET_ESP32S2
#define MAX_LOG_LINES 128
#else
#define MAX_LOG_LINES 200
#endif
#define MAX_LOG_ENTRY 128 // max length of one entry

struct LogSnapshot {
  uint64_t end;
  size_t count;
};

LogSnapshot logSnapshot();
bool readLogEntry(const LogSnapshot &snapshot, size_t offset, bool newestFirst,
                  char (&entry)[MAX_LOG_ENTRY]);

/* P R O T O T Y P E S ********************************************************/
void messageSetup();
void messageCyclic();
void addLogBuffer(const char *message);
void clearLogBuffer();
void setLogLevel(uint8_t level);
