# Google Cloud Credentials Setup

## Security Notice
This project uses Google Cloud Services and requires proper credential management. **Never commit credentials files to git!**

## Setup Instructions

### 1. Obtain Service Account Credentials
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project or create a new one
3. Navigate to "IAM & Admin" > "Service Accounts"
4. Create a service account or use an existing one
5. Generate a new key (JSON format)
6. Download the credentials file

### 2. Configure Environment Variables
Instead of using a credentials file directly, set up environment variables in your `.env` file:

```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
```

### 3. Alternative: Credentials File (Local Development Only)
If you prefer to use a credentials file for local development:

1. Copy `credentials-template.json` to a new file (e.g., `credentials.json`)
2. Fill in your actual credentials
3. **IMPORTANT**: Never commit this file to git - it's already in `.gitignore`

### 4. Production Deployment
For production environments, use:
- Google Cloud's Application Default Credentials (ADC)
- Kubernetes secrets
- Environment variables in your hosting platform
- Google Cloud Secret Manager

## Security Best Practices
- Use environment variables in production
- Rotate credentials regularly
- Use least-privilege access (minimal required permissions)
- Never share credentials in plain text
- Use Google Cloud IAM for fine-grained access control

## Troubleshooting
If you encounter authentication errors:
1. Verify your environment variables are set correctly
2. Check that your service account has the required permissions
3. Ensure the private key format includes proper newlines (\n)
4. Test with `gcloud auth application-default print-access-token`