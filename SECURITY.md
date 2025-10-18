# Security

## Credential Storage

moneyflow provides secure credential storage to avoid storing plaintext passwords or requiring environment variables.

### How It Works

1. **Encryption**: Credentials are encrypted using Fernet (symmetric encryption with AES-128)
2. **Key Derivation**: Your encryption password is converted to a key using PBKDF2-HMAC-SHA256 with 100,000 iterations
3. **Salt**: A random 16-byte salt is generated per installation
4. **File Permissions**: Credential files are set to 0600 (readable only by owner)

### What's Stored

The `~/.moneyflow/credentials.enc` file contains:
- Monarch Money email address
- Monarch Money password
- TOTP/OTP secret for 2FA

### Why This Approach?

**Better than environment variables:**
- Environment variables can leak into shell history
- They can be accidentally committed to version control
- They're visible to other processes on the system

**Better than plaintext config files:**
- Credentials are encrypted at rest
- Requires password to decrypt
- Password is never written to disk

**Better than system keychains:**
- Portable across all platforms (Windows, macOS, Linux)
- No OS-specific dependencies
- Simple implementation

### Recommendations

1. **Use a strong encryption password**
   - At least 12 characters
   - Mix of letters, numbers, symbols
   - Don't reuse your Monarch password

2. **Protect your config directory**
   ```bash
   chmod 700 ~/.moneyflow
   chmod 600 ~/.moneyflow/*
   ```

3. **Backup your TOTP secret**
   - Store it securely (password manager, encrypted backup)
   - If you lose it, you'll need to reset 2FA on Monarch Money

4. **Delete credentials when done**
   ```bash
   rm ~/.moneyflow/credentials.enc
   rm ~/.moneyflow/salt
   ```

### Security Audit

The encryption implementation uses:
- `cryptography` library (widely audited, industry standard)
- Fernet (spec: https://github.com/fernet/spec)
- PBKDF2 with 100,000 iterations (OWASP minimum recommendation)
- SHA-256 hash function
- Random salt per installation

### Threat Model

**Protected against:**
- Casual file system access (files are encrypted)
- Accidental commits to git (credentials not in plaintext)
- Process inspection (credentials not in environment)

**Not protected against:**
- Attacker with your encryption password
- Memory dumps while TUI is running
- Keyloggers or screen capture
- Root/admin access to your system

### Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly rather than opening a public issue.
