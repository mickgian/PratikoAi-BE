#!/bin/bash

# PratikoAI Vercel Deployment Script
echo "🚀 Deploying PratikoAI Landing Page to Vercel"
echo "============================================="

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Please run this script from the project root."
    exit 1
fi

# Check if build works locally
echo "🔨 Testing build locally..."
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Build failed. Please fix build errors before deploying."
    exit 1
fi

echo "✅ Build successful!"

# Deploy to Vercel
echo "📦 Deploying to Vercel..."

# Check if user is logged in to Vercel
if ! npx vercel whoami > /dev/null 2>&1; then
    echo "🔐 Please login to Vercel first:"
    echo "   npx vercel login"
    echo ""
    echo "Or set your API token:"
    echo "   export VERCEL_TOKEN=your_token_here"
    exit 1
fi

# Deploy
echo "🚀 Deploying..."
npx vercel --prod

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo "Your PratikoAI landing page is now live!"
    echo ""
    echo "📊 Next steps:"
    echo "  1. Visit your deployment URL to verify everything works"
    echo "  2. Set up custom domain if needed: npx vercel domains"
    echo "  3. Configure environment variables: npx vercel env"
    echo "  4. Set up monitoring and analytics"
else
    echo "❌ Deployment failed. Please check the error messages above."
    exit 1
fi