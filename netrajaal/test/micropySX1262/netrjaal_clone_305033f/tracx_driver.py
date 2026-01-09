"""
TracX-1b Unified Driver
Simple driver for GPS, Internet connectivity, and HTTP POST uploads
Based on EC200U AT commands
"""

import time
import json
from machine import UART

# Try to import re for regex, fallback to manual parsing
try:
    import re
    HAS_RE = True
except ImportError:
    HAS_RE = False

# Try to import logger, fallback to print
try:
    from logger import logger
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False
    class SimpleLogger:
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
    logger = SimpleLogger()

# Configuration
UART_ID = 1
BAUDRATE = 115200


class TracX:
    """Unified driver for TracX-1b module (GPS, Internet, Time)"""
    
    def __init__(self, uart_id=UART_ID, baudrate=BAUDRATE):
        """Initialize TracX driver with UART configuration"""
        self.uart_id = uart_id
        self.baudrate = baudrate
        self.uart = None
        self.gps_initialized = False
        self.internet_initialized = False
    
    def _send_at(self, cmd, wait_ms=1000, retry=3):
        """Send AT command and return response"""
        if self.uart is None:
            self.uart = UART(self.uart_id, self.baudrate, timeout=2000)
            logger.debug("[TRACX] UART initialized, waiting for module...")
            time.sleep_ms(2000)  # Wait for module to initialize (like examples)
        
        # Clear buffer before sending
        while self.uart.any():
            self.uart.read()
        
        for attempt in range(retry):
            logger.debug(f"[TRACX] Sending: {cmd} (attempt {attempt+1}/{retry})")
            self.uart.write((cmd + "\r\n").encode())
            
            end = time.ticks_ms() + wait_ms
            resp = b""
            while time.ticks_diff(end, time.ticks_ms()) > 0:
                if self.uart.any():
                    resp += self.uart.read()
                time.sleep_ms(10)
            
            # Check if we got a response
            if len(resp) > 0:
                try:
                    resp_preview = resp[:200] if len(resp) > 200 else resp
                    resp_text = resp_preview.decode('ascii')
                    logger.debug(f"[TRACX] Response: {resp_text}")
                except:
                    logger.debug(f"[TRACX] Response: {len(resp)} bytes (decode failed)")
                return resp
            elif attempt < retry - 1:
                # No response, retry after delay
                logger.debug(f"[TRACX] No response, retrying...")
                time.sleep_ms(500)
        
        # No response after retries
        logger.debug("[TRACX] Response: (empty after retries)")
        return b""
    
    def _check_response(self, resp, expected="OK"):
        """Check if response contains expected string"""
        return expected.encode() in resp
    
    def initialize_gps(self):
        """Enable GPS/GNSS on TracX-1b module - matches working example"""
        logger.info("[TRACX] Initializing GPS...")
        
        # Initialize UART if not already done (matches example: UART created at module level)
        if self.uart is None:
            self.uart = UART(self.uart_id, self.baudrate, timeout=2000)
            logger.debug("[TRACX] UART initialized, waiting for module...")
            time.sleep_ms(2000)  # Wait for module to initialize (matches example)
        
        # Test AT command (matches example: "AT" with 500ms timeout)
        resp = self._send_at("AT", 1000, retry=3)
        if not self._check_response(resp):
            logger.error("[TRACX] No AT response!")
            return False
        logger.debug("[TRACX] Module responding to AT")
        
        # Disable echo (matches example: "ATE0")
        self._send_at("ATE0", 500)
        
        # Enable GPS (matches example: "AT+QGPS=1" with 3000ms timeout)
        resp = self._send_at("AT+QGPS=1", 5000)
        if self._check_response(resp):
            self.gps_initialized = True
            logger.info("[TRACX] GPS initialized successfully")
            return True
        
        logger.error("[TRACX] GPS initialization failed")
        return False
    
    def get_gps_location(self):
        """
        Query GPS location
        Returns: (lat, lon, time_str) tuple or (None, None, None) if no fix
        """
        if not self.gps_initialized:
            if not self.initialize_gps():
                return None, None, None
        
        resp = self._send_at("AT+QGPSLOC?", 3000)
        return self._parse_gps_response(resp)
    
    def _utc_to_local(self, dd, mo, yy, hh, mm, ss, tz_offset=5.5):
        """Convert UTC time to local time using timezone offset (IST = UTC+5:30)"""
        dd, mo = int(dd), int(mo)
        # Add timezone offset to UTC time (in seconds)
        secs = int(hh) * 3600 + int(mm) * 60 + int(ss) + int(tz_offset * 3600)
        # Handle day rollover (next/previous day)
        if secs >= 86400:
            secs -= 86400
            dd += 1
        elif secs < 0:
            secs += 86400
            dd -= 1
        # Convert back to hours, minutes, seconds
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return "%02d/%02d/20%s %02d:%02d:%02d" % (dd, mo, yy, h, m, s)
    
    def _parse_gps_response(self, resp):
        """Parse AT+QGPSLOC? response - returns (lat, lon, time_str) or (None, None, None)"""
        try:
            text = resp.decode("ascii")
        except:
            return None, None, None
        
        if "+CME ERROR" in text or "+QGPSLOC:" not in text:
            return None, None, None
        
        for line in text.split("\n"):
            if not line.startswith("+QGPSLOC:"):
                continue
            
            # Format: +QGPSLOC: hhmmss.sss,ddmm.mmmmN/S,dddmm.mmmmE/W,...,ddmmyy
            parts = line.split(":")[1].strip().split(",")
            if len(parts) < 10:
                continue
            
            utc, lat_f, lon_f, date = parts[0], parts[1], parts[2], parts[9]
            hh, mm, ss = utc[0:2], utc[2:4], utc[4:6]
            dd, mo, yy = date[0:2], date[2:4], date[4:6]
            
            # Convert UTC to local time (IST = UTC+5:30)
            timestr = self._utc_to_local(dd, mo, yy, hh, mm, ss, tz_offset=5.5)
            
            # Convert NMEA format to decimal degrees
            def to_deg(s, is_lat):
                d = int(s[0:2 if is_lat else 3])
                m = float(s[2 if is_lat else 3:])
                return d + m / 60.0
            
            lat = to_deg(lat_f[:-1], True)
            lon = to_deg(lon_f[:-1], False)
            
            # Handle hemisphere (S/W = negative)
            if lat_f[-1] == "S":
                lat = -lat
            if lon_f[-1] == "W":
                lon = -lon
            
            return lat, lon, timestr
        
        return None, None, None
    
    def get_gps_time_components(self, time_str):
        """
        Parse GPS time string and return RTC-compatible tuple
        Args: time_str in format "DD/MM/YYYY HH:MM:SS" (local time)
        Returns: (year, month, day, hour, minute, second, weekday, yearday) tuple or None
        """
        if time_str is None:
            return None
        
        try:
            # Parse time string: "DD/MM/YYYY HH:MM:SS"
            date_part, time_part = time_str.split(" ")
            dd, mm, yyyy = date_part.split("/")
            hh, mm_sec, ss = time_part.split(":")
            
            # RTC.datetime format: (year, month, day, weekday, hour, minute, second, microsecond)
            # weekday: 0=Monday, 6=Sunday (can be 0 for now)
            # yearday: day of year (can be 0 for now)
            return (int(yyyy), int(mm), int(dd), 0, int(hh), int(mm_sec), int(ss), 0)
        except Exception as e:
            logger.error(f"[TRACX] Failed to parse time string '{time_str}': {e}")
            return None
    
    def initialize_internet(self):
        """Initialize and activate internet connection"""
        logger.info("[TRACX] Initializing internet...")
        
        # Initialize UART if not already done
        if self.uart is None:
            logger.debug(f"[TRACX] Initializing UART (id={self.uart_id}, baud={self.baudrate})...")
            try:
                self.uart = UART(self.uart_id, self.baudrate, timeout=2000)
                logger.debug("[TRACX] UART created, waiting for module to be ready...")
                time.sleep_ms(2000)  # Wait for module to initialize
            except Exception as e:
                logger.error(f"[TRACX] UART initialization failed: {e}")
                return False
        
        # Test AT command with multiple retries - module may need time to wake up
        logger.debug("[TRACX] Testing AT command communication...")
        resp = None
        for attempt in range(5):  # Try up to 5 times
            resp = self._send_at("AT", 3000, retry=1)  # Don't retry in _send_at, we retry here
            if self._check_response(resp):
                logger.debug("[TRACX] Module responding to AT commands")
                break
            if attempt < 4:
                logger.debug(f"[TRACX] No AT response, waiting and retrying ({attempt+1}/5)...")
                if attempt == 2:
                    # After 3 failed attempts, try reinitializing UART
                    logger.debug("[TRACX] Attempting UART reinitialization...")
                    self._reinit_uart()
                time.sleep_ms(1000)  # Wait 1 second between attempts
        else:
            logger.error("[TRACX] No AT response after 5 attempts!")
            logger.error(f"[TRACX] UART: id={self.uart_id}, baud={self.baudrate}, timeout=2000")
            logger.error("[TRACX] Check: 1) Module powered on, 2) UART pins connected, 3) Correct baudrate")
            try:
                if resp:
                    logger.error(f"[TRACX] Last response: {resp[:100]}")
            except:
                pass
            return False
        
        # Disable echo for cleaner output
        self._send_at("ATE0", 1000)
        
        # Check network registration
        resp = self._send_at("AT+CREG?", 3000)
        try:
            reg_text = resp[:200].decode('ascii')
            logger.debug(f"[TRACX] Network reg: {reg_text}")
        except:
            logger.debug(f"[TRACX] Network reg: {len(resp)} bytes")
        
        # Check if PDP context already active
        resp = self._send_at("AT+QIACT?", 3000)
        if b"+QIACT:" in resp:
            try:
                text = resp.decode("ascii")
                if ",1" in text or "+QIACT: 1" in text:
                    self.internet_initialized = True
                    logger.info("[TRACX] Internet already active")
                    return True
            except:
                pass
        
        # Activate PDP context
        logger.debug("[TRACX] Activating PDP context...")
        resp = self._send_at("AT+QIACT=1", 10000)  # Longer timeout for activation
        if self._check_response(resp):
            self.internet_initialized = True
            logger.info("[TRACX] Internet activated successfully")
            return True
        
        logger.error(f"[TRACX] Internet activation failed")
        try:
            logger.error(f"[TRACX] Response: {resp[:200].decode('ascii')}")
        except:
            logger.error(f"[TRACX] Response: {len(resp)} bytes")
        return False
    
    def _clear_uart_buffer(self):
        """Clear UART buffer - helper method for consistent buffer clearing"""
        if self.uart:
            while self.uart.any():
                self.uart.read()
            time.sleep_ms(50)  # Brief delay after clearing
    
    def _reinit_uart(self):
        """Reinitialize UART - useful if module isn't responding"""
        logger.debug("[TRACX] Reinitializing UART...")
        try:
            if self.uart:
                # Try to close/reset if possible
                pass
            self.uart = UART(self.uart_id, self.baudrate, timeout=2000)
            time.sleep_ms(2000)  # Wait for module to stabilize
            logger.debug("[TRACX] UART reinitialized")
            return True
        except Exception as e:
            logger.error(f"[TRACX] UART reinit failed: {e}")
            return False
    
    def upload_data(self, payload, url, max_retries=2):
        """
        Upload data via HTTP POST - optimized for speed and reliability
        Returns: dict with 'status_code' key (0 = failure, 200 = success)
        """
        logger.debug("[TRACX] Starting HTTP POST upload...")
        
        # Ensure UART is initialized first
        if self.uart is None:
            self.uart = UART(self.uart_id, self.baudrate, timeout=2000)
            time.sleep_ms(500)  # Reduced wait time
        
        # Ensure internet is initialized
        if not self.internet_initialized:
            if not self.initialize_internet():
                logger.error("[TRACX] Internet not initialized")
                return {'status_code': 0}
        
        # Retry loop for robust uploads
        for retry in range(max_retries + 1):
            if retry > 0:
                logger.debug(f"[TRACX] Retry attempt {retry}/{max_retries}")
                # Cleanup and wait before retry
                self._cleanup_http_service()
                time.sleep_ms(1000)
            
            try:
                # Step 0: Cleanup HTTP service state before starting (critical for avoiding 711 errors)
                self._cleanup_http_service()
                
                # Convert payload to JSON
                json_safe_payload = {}
                for key, value in payload.items():
                    if isinstance(value, bytes):
                        try:
                            decoded = value.decode('ascii')
                            json_safe_payload[key] = decoded.rstrip('\n\r')
                        except Exception as e:
                            logger.error(f"[TRACX] Failed to decode bytes for key {key}: {e}")
                            json_safe_payload[key] = ""
                    else:
                        json_safe_payload[key] = value
                
                json_str = json.dumps(json_safe_payload)
                json_bytes = json_str.encode('utf-8')
                json_len = len(json_bytes)
                
                logger.debug(f"[TRACX] JSON payload size: {json_len} bytes")
                
                # Step 1: Configure HTTP context ID (quick config)
                self._clear_uart_buffer()
                if not self._check_response(self._send_at('AT+QHTTPCFG="contextid",1', 2000)):
                    logger.error("[TRACX] HTTP context config failed")
                    continue  # Retry
                
                # Step 2: Set Content-Type header
                self._clear_uart_buffer()
                header = "Content-Type: application/json"
                if not self._check_response(self._send_at(f'AT+QHTTPCFG="requestheader",1,"{header}"', 2000)):
                    logger.error("[TRACX] Header config failed")
                    continue  # Retry
                
                # Step 3: Set URL - AT+QHTTPURL expects CONNECT prompt
                self._clear_uart_buffer()
                url_len = len(url)
                self.uart.write(f'AT+QHTTPURL={url_len},80\r\n'.encode())
                time.sleep_ms(300)  # Reduced wait
                
                # Wait for CONNECT response (faster timeout)
                end = time.ticks_ms() + 5000  # Reduced from 10000
                resp = b""
                while time.ticks_diff(end, time.ticks_ms()) > 0:
                    if self.uart.any():
                        resp += self.uart.read()
                    if b"CONNECT" in resp:
                        break
                    if b"ERROR" in resp or b"+CME ERROR" in resp:
                        # Check for 711 error specifically
                        if b"711" in resp:
                            logger.warning("[TRACX] HTTP service busy (711), cleaning up and retrying...")
                            self._cleanup_http_service()
                            time.sleep_ms(500)
                            break  # Exit loop to retry
                        try:
                            logger.error(f"[TRACX] URL CONNECT failed: {resp.decode('ascii')[:200]}")
                        except:
                            pass
                        break  # Exit to retry
                    time.sleep_ms(50)  # Faster polling
                
                if b"CONNECT" not in resp:
                    if retry < max_retries:
                        continue  # Retry
                    try:
                        logger.error(f"[TRACX] No CONNECT for URL: {resp.decode('ascii')[:200]}")
                    except:
                        pass
                    return {'status_code': 0}
                
                # Send URL data and terminate with Ctrl+Z
                self.uart.write(url.encode('utf-8'))
                self.uart.write(b'\x1A')  # Ctrl+Z
                time.sleep_ms(200)  # Reduced wait
                
                # Wait for OK after URL (faster timeout)
                end = time.ticks_ms() + 5000  # Reduced from 8000
                resp = b""
                while time.ticks_diff(end, time.ticks_ms()) > 0:
                    if self.uart.any():
                        resp += self.uart.read()
                    if b"OK" in resp:
                        break
                    if b"ERROR" in resp or b"+CME ERROR" in resp:
                        if b"711" in resp:
                            if retry < max_retries:
                                continue  # Retry
                        try:
                            logger.error(f"[TRACX] URL send failed: {resp.decode('ascii')[:200]}")
                        except:
                            pass
                        break
                    time.sleep_ms(50)
                
                if b"OK" not in resp:
                    if retry < max_retries:
                        continue  # Retry
                    return {'status_code': 0}
                
                # Step 4: Send POST data - AT+QHTTPPOST expects CONNECT prompt
                self._clear_uart_buffer()
                self.uart.write(f'AT+QHTTPPOST={json_len},80,80\r\n'.encode())
                time.sleep_ms(300)  # Reduced wait
                
                # Wait for CONNECT response for POST
                end = time.ticks_ms() + 5000  # Reduced from 10000
                resp = b""
                while time.ticks_diff(end, time.ticks_ms()) > 0:
                    if self.uart.any():
                        resp += self.uart.read()
                    if b"CONNECT" in resp:
                        break
                    if b"ERROR" in resp or b"+CME ERROR" in resp:
                        if b"711" in resp:
                            if retry < max_retries:
                                continue  # Retry
                        break
                    time.sleep_ms(50)
                
                if b"CONNECT" not in resp:
                    if retry < max_retries:
                        continue  # Retry
                    return {'status_code': 0}
                
                # Send JSON data and terminate with Ctrl+Z
                self.uart.write(json_bytes)
                self.uart.write(b'\x1A')  # Ctrl+Z
                time.sleep_ms(200)  # Reduced wait
                
                # Wait for POST confirmation (OK) - optimized timeout based on payload size
                post_timeout = min(15000, max(5000, json_len // 100))  # Dynamic timeout: 5-15s based on size
                end = time.ticks_ms() + post_timeout
                resp = b""
                while time.ticks_diff(end, time.ticks_ms()) > 0:
                    if self.uart.any():
                        resp += self.uart.read()
                    if b"OK" in resp:
                        break
                    if b"ERROR" in resp or b"+CME ERROR" in resp:
                        if b"711" in resp:
                            if retry < max_retries:
                                continue  # Retry
                        break
                    time.sleep_ms(50)
                
                if b"OK" not in resp:
                    if retry < max_retries:
                        continue  # Retry
                    return {'status_code': 0}
                
                # Step 5: Wait for server to process (reduced wait time)
                time.sleep_ms(2000)  # Reduced from 5000
                
                # Step 6: Read HTTP response (faster timeout)
                self._clear_uart_buffer()
                resp = self._send_at("AT+QHTTPREAD=500,80", 10000)  # Reduced from 30000
                
                # Parse HTTP status code
                status_code = self._parse_http_status(resp)
                
                # Cleanup HTTP service after successful/failed request
                self._cleanup_http_service()
                
                if status_code == 200:
                    logger.info(f"[TRACX] Upload successful: status_code={status_code}")
                    return {'status_code': status_code}
                elif status_code > 0 and retry < max_retries:
                    # Server error, but got response - retry
                    logger.warning(f"[TRACX] Server returned {status_code}, retrying...")
                    continue
                else:
                    logger.error(f"[TRACX] Upload failed: status_code={status_code}")
                    return {'status_code': status_code}
                    
            except Exception as e:
                logger.error(f"[TRACX] Upload exception: {e}")
                self._cleanup_http_service()
                if retry < max_retries:
                    continue  # Retry
                return {'status_code': 0}
        
        # All retries exhausted
        logger.error("[TRACX] Upload failed after all retries")
        return {'status_code': 0}
    
    def _cleanup_http_service(self):
        """Stop HTTP service to ensure clean state - prevents 711 errors"""
        try:
            self._clear_uart_buffer()
            self._send_at("AT+QHTTPSTOP", 1000)  # Stop any ongoing HTTP operation
            time.sleep_ms(200)  # Brief wait for cleanup
        except:
            pass
    
    def _parse_http_status(self, resp):
        """Parse HTTP status code from response"""
        status_code = 0
        try:
            resp_text = resp.decode("ascii")
            
            # Method 1: Look for HTTP status line
            for line in resp_text.split('\n'):
                line = line.strip()
                if line.startswith("HTTP/"):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            status_code = int(parts[1])
                            logger.info(f"[TRACX] HTTP Status: {status_code} (from status line)")
                            return status_code
                        except ValueError:
                            pass
            
            # Method 2: Regex search
            if status_code == 0 and HAS_RE:
                try:
                    match = re.search(r'HTTP/\d\.\d\s+(\d{3})', resp_text)
                    if match:
                        status_code = int(match.group(1))
                        logger.info(f"[TRACX] HTTP Status: {status_code} (from regex)")
                        return status_code
                except:
                    pass
            
            # Method 3: Check response content
            if status_code == 0:
                if b"200" in resp or b"201" in resp or b"202" in resp:
                    status_code = 200
                    logger.info(f"[TRACX] HTTP Status: {status_code} (inferred)")
                elif b"+QHTTPREAD:" in resp and b"OK" in resp:
                    if b"404" not in resp and b"500" not in resp and b"403" not in resp:
                        status_code = 200
                        logger.info(f"[TRACX] HTTP Status: {status_code} (assumed from OK)")
                elif b"404" in resp:
                    status_code = 404
                    logger.error(f"[TRACX] HTTP Status: {status_code} (Not Found)")
                elif b"500" in resp or b"502" in resp or b"503" in resp:
                    status_code = 500
                    logger.error(f"[TRACX] HTTP Status: {status_code} (Server Error)")
                        
        except Exception as e:
            logger.error(f"[TRACX] Error parsing response: {e}")
        
        if status_code == 0:
            logger.error("[TRACX] Could not determine HTTP status code")
        
        return status_code

