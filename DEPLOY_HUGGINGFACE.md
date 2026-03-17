# 🚀 Deploy to HuggingFace Spaces

This guide shows how to deploy the Veg Vibe application to HuggingFace Spaces.

## Prerequisites

- HuggingFace account (create at https://huggingface.co)
- Git installed locally
- GitHub account with your Veg-Vibe repo

## 📋 Steps

### 1. Create a New Space on HuggingFace

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. Fill in:
   - **Space name**: `veg-vibe` (or your preferred name)
   - **Select the Space SDK**: Choose **"Docker"**
   - **License**: Select any (MIT recommended)
   - **Visibility**: Public (or Private)
4. Create the Space

### 2. Clone Your Space Repository

```bash
# Copy the clone command from your Space page
git clone https://huggingface.co/spaces/YOUR_USERNAME/veg-vibe
cd veg-vibe
```

### 3. Add Your Project Files

```bash
# Add the Dockerfile for Spaces
cp /path/to/Veg-Vibe/Dockerfile.spaces ./Dockerfile

# Copy backend
cp -r /path/to/Veg-Vibe/backend ./backend

# Copy frontend (optional - will be built from Dockerfile)
cp -r /path/to/Veg-Vibe/frontend ./frontend

# Copy recipe data
cp /path/to/Veg-Vibe/vegan_recipes.csv .
cp -r /path/to/Veg-Vibe/HuggingFaceSpaces . || true

# Create a README for the Space
echo "# 🥬 Veg Vibe - Vegan Recipe Recommender" > README.md
echo "Get personalized vegan recipe recommendations based on ingredients!" >> README.md
```

### 4. Commit and Push

```bash
git add .
git commit -m "🚀 Deploy Veg Vibe to HuggingFace Spaces"
git push
```

**That's it!** HuggingFace will automatically:

- Detect the `Dockerfile`
- Build your application
- Deploy it
- Assign you a public URL

### 5. Your Space is Live!

Once the build completes (5-10 minutes), you'll get a URL like:

```
https://huggingface.co/spaces/YOUR_USERNAME/veg-vibe
```

The app will be accessible at that URL directly!

---

## 🔧 Environment & Configuration

### Important Notes

- **Port**: HuggingFace uses port `7860` (already configured in Dockerfile.spaces)
- **Build time**: First deploy takes 5-10 minutes
- **Subsequent updates**: Usually 2-3 minutes
- **Storage**: You have persistent storage at `/data` if needed (update Dockerfile if using)

### Backend API Docs

Once deployed, access:

- 🌐 **Frontend**: `https://huggingface.co/spaces/YOUR_USERNAME/veg-vibe`
- 📖 **API Docs**: Add `/docs` to your Space URL
- 🔄 **Health Check**: Add `/health` to your Space URL

---

## 📝 Updating Your Deployment

To update the Space with new changes:

1. Make changes locally in your repo
2. Build and test locally
3. Push to GitHub (if using GitHub as source)
4. Update your Space repo:
   ```bash
   cd your-space-directory
   git pull  # Get latest from your source
   git push  # Push to HuggingFace
   ```

HuggingFace will automatically rebuild!

---

## 🐛 Troubleshooting

### Build Fails

Check the build logs in the Space settings:

- Click **"Settings"** → **"Code"**
- Look for error messages in the build output

Common issues:

- Missing recipe CSV file → Add to repo
- Python version incompatibility → Check Python version in Dockerfile
- Node.js memory issues → Build occasionally times out (usually succeeds on retry)

### App Runs but Frontend Not Loading

- Check browser console for errors (F12)
- Ensure frontend built correctly in Docker
- Verify static files mounted in `app/main.py`

### Recipes Not Loading

- Verify `vegan_recipes.csv` is in the repo
- Check it's in the correct path for the Docker container
- Look at Space logs for errors

---

## 💾 Updating Recipe Data

To update recipes:

1. Replace `vegan_recipes.csv` in your repo
2. Push to Git
3. HuggingFace rebuilds automatically

---

## 🎨 Customize Your Space

In HuggingFace Space settings:

- Add a cool emoji to the Space name
- Write a description
- Add badges
- Pin the Space to your profile

---

## 📚 Resources

- [HuggingFace Spaces Documentation](https://huggingface.co/docs/hub/spaces)
- [Docker Deployments on Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Your Veg Vibe GitHub](https://github.com/cereal-d3v/Veg-Vibe)

---

**Happy Deploying! 🌱**
