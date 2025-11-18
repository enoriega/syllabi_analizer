# Anti-Crawler Defeat Techniques

This document explains the techniques implemented in `classify_programs.py` to defeat anti-crawler protection.

## Techniques Implemented

### 1. **Session Reuse (Single-threaded Mode)**
- **What**: Instead of creating a new browser instance for each request, we reuse the same browser session
- **Why**: Repeatedly creating/destroying browser instances looks suspicious. Reusing a session mimics human behavior
- **Implementation**: Global `_global_driver` variable that persists across requests when `reuse_driver=True`
- **Benefit**: Maintains cookies, session state, and browsing history like a real user

### 2. **Random Delays**
- **What**: Add random delays between 2-5 seconds before each request
- **Why**: Bots typically make requests at consistent intervals. Humans have irregular timing
- **Implementation**: `time.sleep(random.uniform(2, 5))` before each page load
- **Benefit**: Makes traffic pattern appear more human-like

### 3. **User Agent Rotation**
- **What**: Randomly select from multiple realistic user agent strings
- **Why**: Prevents detection based on consistent user agent patterns
- **Implementation**: Random selection from list of 4 different browsers/OS combinations
- **Benefit**: Distributes requests across different "browsers"

### 4. **WebDriver Property Hiding**
- **What**: Remove/modify JavaScript properties that reveal automation
- **Why**: Sites check `navigator.webdriver` and other properties to detect Selenium
- **Implementation**:
  ```javascript
  Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
  ```
- **Benefit**: Makes the browser appear as non-automated

### 5. **Chrome DevTools Protocol (CDP) Commands**
- **What**: Use CDP to override network-level properties
- **Why**: Provides deeper control than regular Selenium options
- **Implementation**: `driver.execute_cdp_cmd('Network.setUserAgentOverride')`
- **Benefit**: Overrides user agent at network level, harder to detect

### 6. **Browser Fingerprint Spoofing**
- **What**: Inject JavaScript to fake browser properties
- **Why**: Sites fingerprint browsers by checking plugins, languages, platform
- **Implementation**:
  ```javascript
  Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
  Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
  window.chrome = { runtime: {} };
  ```
- **Benefit**: Browser appears as regular Chrome with normal properties

### 7. **Disable Automation Indicators**
- **What**: Remove Chrome flags that indicate automation
- **Why**: Chrome adds special flags when running under automation
- **Implementation**:
  ```python
  chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
  chrome_options.add_experimental_option('useAutomationExtension', False)
  ```
- **Benefit**: Removes visible automation indicators

### 8. **Non-Headless Mode with Off-Screen Positioning**
- **What**: Run browser with GUI but position windows off-screen
- **Why**: Headless mode is easily detected; having a GUI makes it appear more legitimate
- **Implementation**: `chrome_options.add_argument("--window-position=-2400,-2400")`
- **Benefit**: Avoids headless detection while keeping browser "invisible"

### 9. **Natural Browsing Behavior**
- **What**: Wait for page to fully render, scroll might occur naturally
- **Why**: Bots often don't wait for JavaScript to execute fully
- **Implementation**: Multiple `time.sleep()` calls after page load
- **Benefit**: Gives JavaScript time to render, appears more patient like a human

### 10. **Rate Limiting**
- **What**: Built-in delays prevent rapid-fire requests
- **Why**: Too many requests too quickly triggers rate limiters
- **Implementation**: Combined delays total 4-9 seconds per request
- **Benefit**: Stays under rate limit thresholds

## Usage Modes

### Single-Threaded Mode (Recommended for Anti-Crawler)
```bash
uv run python classify_programs.py --workers 1 --input ua_programs.json --output output.json
```

**Advantages:**
- Reuses same browser session (most effective anti-detection)
- Allows CAPTCHA interaction
- Maintains natural browsing history
- Lower memory usage (one browser instance)

**Disadvantages:**
- Slower (sequential processing)
- Takes ~5-10 seconds per program

### Multi-Threaded Mode (Faster but More Detectable)
```bash
uv run python classify_programs.py --workers 10 --input ua_programs.json --output output.json
```

**Advantages:**
- Much faster (parallel processing)
- Processes 10 programs simultaneously

**Disadvantages:**
- Creates 10 separate browser instances
- More likely to trigger anti-crawler measures
- Cannot maintain session continuity
- Cannot interact with CAPTCHAs easily

## Additional Strategies Not Yet Implemented

### 1. **Proxy Rotation**
- Use different IP addresses for requests
- Requires proxy service (costs money)
- Implementation: `chrome_options.add_argument(f'--proxy-server={proxy}')`

### 2. **Cookie Management**
- Save/load cookies from manual browsing session
- Similar to `crawl_programs_with_cookies.py` approach
- Would need manual CAPTCHA solving once, then reuse session

### 3. **Request Header Manipulation**
- Add realistic Accept, Accept-Language, Accept-Encoding headers
- Mimic real browser request headers more closely

### 4. **Mouse Movement Simulation**
- Use `ActionChains` to simulate human mouse movements
- Click elements, scroll naturally
- More complex but more convincing

### 5. **Browser Profile Reuse**
- Use a real Chrome profile with browsing history
- `chrome_options.add_argument(f'--user-data-dir=/path/to/profile')`
- Would have cookies, history, extensions

## Monitoring and Debugging

If you're still getting blocked:

1. **Check the page source**: Look for CAPTCHA or block messages
2. **Monitor delays**: Ensure random delays are working
3. **Check driver reuse**: Verify `_global_driver` is being reused in single-threaded mode
4. **Increase delays**: Try `time.sleep(random.uniform(5, 10))` for more cautious crawling
5. **Test manually**: Try the same access pattern manually to see if you get blocked

## Best Practices

1. **Start with single-threaded mode** - Most effective for anti-detection
2. **Use `--limit` for testing** - Test with 5-10 programs before full run
3. **Be patient** - 1000 programs × 7 seconds = ~2 hours, but it's safer
4. **Respect the site** - Don't try to circumvent reasonable rate limits
5. **Monitor for blocks** - If you see CAPTCHAs, slow down even more
6. **Consider alternatives** - Check if UA provides an API or data export option

## Success Metrics

A successful run should show:
- ✅ No CAPTCHAs after initial load
- ✅ Consistent extraction of program descriptions
- ✅ No "Access Denied" or "Too Many Requests" errors
- ✅ Browser session maintained throughout processing
