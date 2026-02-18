# 🚀 PratikoAI Vercel Deployment Guide

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **API Token**: Get your token from [vercel.com/account/tokens](https://vercel.com/account/tokens)
3. **GitHub Repository** (optional but recommended): Push your code to GitHub

## Quick Deployment

### Option 1: One-Command Deploy (Recommended)

```bash
npm run deploy
```

### Option 2: Manual Steps

1. **Login to Vercel**

```bash
npx vercel login
```

2. **Deploy for Preview**

```bash
npm run deploy:preview
```

3. **Deploy to Production**

```bash
npm run deploy:prod
```

### Option 3: Using API Token

```bash
export VERCEL_TOKEN=your_api_token_here
npx vercel --prod --token $VERCEL_TOKEN
```

## Environment Variables (Optional)

If you need environment variables in production:

1. **Create production env file**

```bash
cp .env.production.template .env.production
# Edit .env.production with your values
```

2. **Set via Vercel CLI**

```bash
npx vercel env add VARIABLE_NAME
```

3. **Set via Vercel Dashboard**

- Go to your project dashboard
- Navigate to Settings → Environment Variables
- Add your variables

## Project Configuration

Your project includes:

- ✅ `vercel.json` - Vercel configuration
- ✅ `deploy.sh` - Automated deployment script
- ✅ Build optimization for production
- ✅ Security headers configured
- ✅ Next.js app router support

## Deployment Features

### Automatic Deployments

- **Preview**: Every push to feature branches
- **Production**: Every push to main branch (if connected to GitHub)

### Performance Features

- ✅ Edge Functions support
- ✅ Static site generation where possible
- ✅ Automatic image optimization
- ✅ CDN distribution worldwide

### Monitoring

- **Analytics**: Available in Vercel dashboard
- **Real User Monitoring**: Automatic
- **Performance Insights**: Built-in

## Custom Domain Setup

After deployment, set up your custom domain:

```bash
# Add domain
npx vercel domains add yourdomain.com

# Check domain status
npx vercel domains ls
```

## Troubleshooting

### Common Issues

**Build Failures**

```bash
# Test build locally first
npm run build

# Check build logs
npx vercel logs your-deployment-url
```

**Environment Variables Not Working**

```bash
# List current env vars
npx vercel env ls

# Add missing env var
npx vercel env add VARIABLE_NAME
```

**Deployment Stuck**

```bash
# Cancel current deployment
npx vercel remove deployment-id

# Redeploy
npm run deploy:prod
```

## Production URLs

After deployment, your site will be available at:

- **Production**: `https://your-project-name.vercel.app`
- **Preview**: `https://your-project-name-git-branch.vercel.app`
- **Custom Domain**: `https://yourdomain.com` (after setup)

## Post-Deployment Checklist

- [ ] Verify all pages load correctly
- [ ] Test responsive design on different devices
- [ ] Check all animations work properly
- [ ] Verify forms and interactions
- [ ] Test performance with Lighthouse
- [ ] Set up custom domain (optional)
- [ ] Configure analytics (optional)
- [ ] Set up monitoring alerts (optional)

## Support

- **Vercel Docs**: [vercel.com/docs](https://vercel.com/docs)
- **Next.js Deployment**: [nextjs.org/docs/deployment](https://nextjs.org/docs/deployment)
- **Vercel Community**: [github.com/vercel/vercel/discussions](https://github.com/vercel/vercel/discussions)

---

Your PratikoAI landing page is now ready for production deployment! 🎉
