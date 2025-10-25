# Pre-Release Checklist for PUMA v1.8.3

## ✅ Before Creating the GitHub Release:

### 1. Verify GitHub Secrets are Set
Go to: https://github.com/ENHANCE-PET/PUMA/settings/secrets/actions

Make sure these secrets exist:
- [ ] `PYPI_API_TOKEN` - Your PyPI API token
- [ ] `DOCKER_USERNAME` - Your Docker Hub username  
- [ ] `DOCKER_PASSWORD` - Your Docker Hub password or access token

### 2. Verify Version
- [x] Current version in `pyproject.toml`: **1.8.3**

### 3. Test Locally (Optional but Recommended)
```bash
# Build package locally
python -m pip install --upgrade pip build
python -m build --sdist --wheel

# Verify the build
ls -la dist/
```

## 🚀 Creating the Release:

1. **Go to GitHub Releases**:
   https://github.com/ENHANCE-PET/PUMA/releases/new

2. **Create a new tag**: `v1.8.3`

3. **Release title**: `Release v1.8.3` (or your preferred title)

4. **Description**: Add your release notes

5. **Click "Publish release"**

## 🤖 What the Workflow Will Do:

Once you publish the release, the workflow will automatically:

1. ✅ Extract version from `pyproject.toml` (1.8.3)
2. ✅ Build Python package (wheel + source distribution)
3. ✅ Publish to PyPI: https://pypi.org/project/pumaz/
4. ✅ Wait 60 seconds for PyPI propagation
5. ✅ Build Docker image for multiple platforms (amd64, arm64)
6. ✅ Push to Docker Hub:
   - `{username}/pumaz:1.8.3`
   - `{username}/pumaz:latest`
7. ✅ Verify release completion

## 📊 Monitoring the Workflow:

After publishing the release, check:
- **Actions tab**: https://github.com/ENHANCE-PET/PUMA/actions
- Look for "Unified Release" workflow run
- Monitor each step's progress

## ⚠️ If Something Goes Wrong:

1. Check the workflow logs in the Actions tab
2. Common issues:
   - Missing or incorrect secrets
   - PyPI package name conflict
   - Docker Hub authentication issues
   - Network timeouts

## 🎉 After Successful Release:

Verify your packages are published:
- **PyPI**: https://pypi.org/project/pumaz/1.8.3/
- **Docker Hub**: https://hub.docker.com/r/{username}/pumaz/tags

You can delete this file after the release is complete.
