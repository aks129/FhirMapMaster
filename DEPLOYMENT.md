# Deployment Guide for Parker FHIR Mapper

## Important Note

**This is a Streamlit application and CANNOT be deployed to Vercel.** Vercel is designed for static sites and serverless functions, not persistent Python servers required by Streamlit.

## Recommended Deployment Platforms

### 1. Streamlit Community Cloud (Recommended) ✅

**Free tier available, designed specifically for Streamlit apps**

#### Steps:
1. Push your code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository: `FhirMapMaster`
6. Set main file path: `app.py`
7. Add secrets in the Advanced settings:
   - `OPENAI_API_KEY = "your-key"`
   - `ANTHROPIC_API_KEY = "your-key"`
8. Click "Deploy"

### 2. Heroku

#### Setup:
1. Create `Procfile`:
```
web: sh setup.sh && streamlit run app.py
```

2. Create `setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "\
[server]\\n\
headless = true\\n\
port = \$PORT\\n\
enableCORS = false\\n\
\\n\
" > ~/.streamlit/config.toml
```

3. Deploy:
```bash
heroku create parker-fhir-mapper
git push heroku main
```

### 3. Railway

#### Steps:
1. Visit [railway.app](https://railway.app)
2. Connect GitHub repository
3. Add environment variables
4. Railway will auto-detect Streamlit and deploy

### 4. Google Cloud Run

#### Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD streamlit run app.py \
    --server.port=8080 \
    --server.address=0.0.0.0 \
    --server.headless=true
```

#### Deploy:
```bash
gcloud run deploy parker-fhir-mapper \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

### 5. Azure Container Instances

Similar to Google Cloud Run, use the Dockerfile above and deploy to Azure Container Instances.

## Local Development

### Install Dependencies:
```bash
pip install -r requirements.txt
```

### Run Locally:
```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## Environment Variables

Set these environment variables or add to `.streamlit/secrets.toml`:

- `OPENAI_API_KEY`: OpenAI API key for LLM suggestions
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude suggestions

## File Structure Required for Deployment

```
FhirMapMaster/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── packages.txt          # System dependencies (if needed)
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── components/           # UI components
├── utils/               # Utility modules
├── cache/              # Cache directories (auto-created)
└── sample_data/        # Sample data files
```

## Testing Deployment

After deployment, test these features:

1. **File Upload**: Try uploading CSV, Excel files
2. **Data Profiling**: Check data analysis works
3. **Resource Selection**: Select FHIR resources
4. **Mapping Interface**: Test field mapping
5. **Export**: Generate and download FHIR bundles

## Troubleshooting

### Common Issues:

1. **"No module named 'streamlit'"**: Ensure requirements.txt is present
2. **Port binding errors**: Check the port configuration matches platform requirements
3. **Memory issues**: Some platforms have memory limits; consider upgrading tier
4. **API key errors**: Ensure environment variables are properly set

## Security Notes

- **NEVER commit API keys to Git**
- Use environment variables or platform-specific secrets management
- The `.streamlit/secrets.toml` file should be in `.gitignore`
- This app should NOT be used with PHI data (as noted in disclaimer)