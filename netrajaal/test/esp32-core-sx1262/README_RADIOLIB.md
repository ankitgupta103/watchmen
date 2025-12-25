# Using RadioLib with ESP-IDF

This project uses RadioLib to simplify the SX1262 driver implementation. RadioLib is an Arduino library, so we need to integrate it with ESP-IDF.

## Option 1: Use Arduino Framework as ESP-IDF Component (Recommended)

ESP-IDF v5.0+ supports Arduino as a component. This is the simplest approach.

### Setup Steps:

1. **Add Arduino component to your project:**

   Create `components/arduino/CMakeLists.txt`:
   ```cmake
   idf_component_register()
   ```

   Or use the official Arduino ESP32 component:
   ```bash
   cd components
   git clone https://github.com/espressif/arduino-esp32.git arduino
   cd arduino
   git submodule update --init --recursive
   ```

2. **Add RadioLib library:**

   ```bash
   cd components/arduino/libraries
   git clone https://github.com/jgromes/RadioLib.git
   ```

3. **Update main/CMakeLists.txt:**

   ```cmake
   idf_component_register(SRCS "main.c"
                                "lora_sx1262.c"
                         INCLUDE_DIRS "."
                         REQUIRES arduino)
   ```

4. **Build and flash:**

   ```bash
   idf.py build
   idf.py flash monitor
   ```

## Option 2: Use PlatformIO (Alternative)

If you prefer PlatformIO (like the LoRa-Test reference), you can use the existing `LoRa-Test` directory which is already configured for PlatformIO with RadioLib.

## Option 3: Manual RadioLib Integration

If you want to use RadioLib without Arduino framework, you'll need to:

1. Clone RadioLib source into your project
2. Adapt RadioLib's SPI/GPIO code to use ESP-IDF APIs
3. This is more complex but gives you full control

## Current Implementation

The `lora_sx1262.c` file is a simplified wrapper around RadioLib that:
- Uses RadioLib's proven SX1262 implementation
- Provides the same API as the low-level version
- Follows the exact patterns from LoRa-Test reference
- Is much simpler (~300 lines vs ~1000 lines)

## Benefits of Using RadioLib

1. **Proven Implementation**: RadioLib is well-tested and widely used
2. **Simpler Code**: ~70% less code than low-level implementation
3. **Direct Reuse**: Uses the exact same logic as LoRa-Test reference
4. **Maintenance**: RadioLib is actively maintained
5. **Features**: Easy to add features like LoRaWAN later if needed

## Comparison

| Aspect | Low-Level | RadioLib Wrapper |
|--------|-----------|------------------|
| Lines of Code | ~1000 | ~300 |
| Complexity | High | Low |
| Maintenance | Manual | RadioLib updates |
| Features | Basic | Full RadioLib features |
| Setup | Simple | Requires Arduino component |

## Note

If you prefer the low-level implementation (without RadioLib), you can use the version from the previous commit. The low-level version is more self-contained but requires more code to maintain.

