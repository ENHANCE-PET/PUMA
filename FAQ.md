
## 🧐 Frequently Asked Questions (FAQ)

### Q1: Having troubles after installing PUMA?

**Problem Description:**

Getting error messages during PUMA installation?  These might be the culprits:

**Error Message:**
```
ERROR: Could not find a version that satisfies the requirement pumaz (from versi
ons: none)
ERROR: No matching distribution found for pumaz
```

**Solution:**

**Double-Check Requirements:**  ✅
- **Python Version:** Make sure you're using Python version *3.10.* You can check this by running python --version in your terminal.
- **RAM Availability:** Ensure you have enough RAM available for your tasks. Moose might require more RAM for complex datasets.
- **Complete Requirements List:** Refer to the official Moose repository for all requirements: [https://github.com/ENHANCE-PET/MOOSE](https://github.com/ENHANCE-PET/MOOSE)
- **Pro Tip:** Avoid spaces in your directory paths. It might cause issues. Use underscores (_) instead.

### Q2: How to fix "IndexError: list index out of range"? ⚠️

**Problem Description:**

PUMA has stopped running and throws this error message? It might be the culprit!

**Solution:**

**Watch Out for Spaces!**  
    - Moose might have trouble with spaces in your directory paths. Try renaming directories to replace spaces with underscores (_). 