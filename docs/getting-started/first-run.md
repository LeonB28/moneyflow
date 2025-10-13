# First Run Setup

## Platform Selection

On your first run, moneyflow will ask you to select a backend:

```
Select your finance platform:
  1. Monarch Money (currently supported)

More backends coming soon (YNAB, Lunch Money, etc.)
```

Currently, only **Monarch Money** is supported, but the architecture is designed for easy addition of other platforms.

---

## Monarch Money Setup

### Prerequisites

You'll need:

1. **Monarch Money account** - Active subscription
2. **2FA secret key** - For automatic login

### Getting Your 2FA Secret

!!! warning "Do this BEFORE running moneyflow"

    1. Log into [Monarch Money](https://app.monarchmoney.com/)
    2. Go to **Settings** → **Security**
    3. **Disable** your existing 2FA
    4. **Re-enable** 2FA
    5. When shown the QR code, click **"Can't scan?"**
    6. Copy the **BASE32 secret** (e.g., `JBSWY3DPEHPK3PXP`)
    7. Save this somewhere secure

### Credential Setup

Launch moneyflow:

```bash
moneyflow
```

You'll be prompted for:

#### 1. Monarch Money Credentials

- **Email**: Your Monarch Money login email
- **Password**: Your Monarch Money password
- **2FA Secret**: The secret key from above

#### 2. Encryption Password

Create a **NEW password** to encrypt your stored credentials:

- This is **only for moneyflow**, not Monarch Money
- Choose something memorable - you'll need it every time you launch
- Minimum 8 characters recommended

!!! info "How Credentials Are Stored"
    Your Monarch Money credentials are encrypted with AES-128 using PBKDF2 key derivation (100,000 iterations) and stored at:

    ```
    ~/.moneyflow/credentials.enc
    ```

    Only you can decrypt them with your encryption password.

### Session Management

moneyflow saves your login session to avoid repeated 2FA:

```
.mm/mm_session.pickle
```

- Sessions typically last 24-48 hours
- Automatically refreshes when expired
- Delete `.mm/` to force fresh login

---

## Subsequent Runs

After initial setup, you only need your **encryption password**:

```bash
moneyflow
# Enter encryption password: ********
# Loading...
```

---

## Reset Credentials

If you forget your encryption password or want to reconfigure:

1. **In the app**: Click "Reset Credentials" on unlock screen
2. **Manually**: Delete credentials and start fresh:
   ```bash
   rm -rf ~/.moneyflow/
   rm -rf .mm/
   moneyflow
   ```

---

## Troubleshooting Setup

### "Incorrect password" when unlocking

- You're entering the **encryption password** (the one YOU created for moneyflow)
- Not your Monarch Money password
- If you forgot it, click "Reset Credentials"

### "Login failed: 401 unauthorized"

- Your 2FA secret might be incorrect
- Get a fresh secret by disabling/re-enabling 2FA
- Remove spaces from the secret key
- Delete `.mm/` and try again

### "Too many login attempts"

moneyflow automatically manages sessions to avoid this, but if it happens:

```bash
# Delete the bad session
rm -rf .mm/

# moneyflow will auto-retry with fresh login
moneyflow
```

---

## Next Steps

- [Quick Start Tutorial](quickstart.md) - Learn the basics
- [Keyboard Shortcuts](../guide/keyboard-shortcuts.md) - Essential keybindings
