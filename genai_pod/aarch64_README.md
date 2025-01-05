# Using `undetected-chromedriver` on ARM64 Systems (e.g., Raspberry Pi)

This guide explains how to set up `undetected-chromedriver` on ARM64 systems like a Raspberry Pi. The default setup of `undetected-chromedriver` assumes an x86_64 architecture and will fail on ARM systems with the error `OSError: [Errno 8] Exec format error`.

This guide includes:

1. Checking your system architecture.
2. Installing the ARM-compatible `chromium-driver`.
3. Copying the driver to a user-writable location.
4. Specifying the correct `driver_executable_path` in your Python code.

---

## 1. **Check System Architecture**

Before proceeding, confirm your system architecture by running:

```bash
uname -m
```

- If you see `aarch64`, your system uses the ARM64 architecture.
- If it is `x86_64`, this guide does not apply.

---

## 2. **Install `chromium-driver` for ARM64**

Install the Chromium driver package using the system's package manager:

```bash
sudo apt update
sudo apt install chromium-driver
```

After installation, verify the installation path:

```bash
which chromedriver
```

The path is typically `/usr/bin/chromedriver`.

---

## 3. **Copy `chromedriver` to a Writable Location**

`undetected-chromedriver` requires a writable copy of the `chromedriver` file. Copy the driver to a local directory:

```bash
cp /usr/bin/chromedriver /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy
```

Replace `<your-username>` with your actual username.

### Verify Architecture of the Driver

Run the following command to ensure the copied driver is compatible with ARM64:

```bash
file /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy
```

The output should include `ARM aarch64`.

---

## 4. **Update utils.py**

Update utils.py to include the `driver_executable_path` parameter, pointing to the copied driver.

Here is the conditional Python code:

```python
def start_chrome(profile_name: str, site: str) -> None:
   ...
    if platform.machine() == "aarch64":
        path = "Paste here your undetected_chromedriver/chromedriver_copy path"
        if not os.path.exists(path):
            logging.error("You have an aarch64 Architecture. "
                          "Please follow the steps in aarch64_README.md!")
            exit(0)
        driver = uc.Chrome(options=chrome_options, driver_executable_path=path)
    else:
        driver = uc.Chrome(options=chrome_options)
    ...
```

### Explanation

- The script checks the system architecture using `platform.machine()`.
- If the system is `aarch64`, it uses the `driver_executable_path` parameter.

---

## 5. **Summary of Steps**

1. Confirm your architecture using `uname -m`.
2. Install `chromium-driver`:
   ```bash
   sudo apt update
   sudo apt install chromium-driver
   ```
3. Copy the driver to a writable location:
   ```bash
   cp /usr/bin/chromedriver /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy
   ```
4. Verify the architecture of the driver:
   ```bash
   file /home/<your-username>/.local/share/undetected_chromedriver/chromedriver_copy
   ```
5. Use `driver_executable_path` in your Python script for ARM64 systems.

---

## Notes

- This process ensures compatibility with ARM64-based systems like Raspberry Pi.
- The instructions assume Debian-based systems (e.g., Raspbian, Ubuntu).

---

Happy coding! 🚀
