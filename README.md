# DevTech Insights - AI-Powered English Tech Blog

> Automated English tech blog targeting Google SEO, monetized via Google AdSense.
> Daily AI-generated articles on Java, Spring Boot, AI/LLM, and system design.

**Stack**: Hexo + GitHub Pages + GitHub Actions + DeepSeek API

---

## 🚀 Quick Start (5 minutes to go live)

### 1. Create GitHub Repository

```bash
# Create a new repo on GitHub named: your-username.github.io
# Then push this project:
git init
git add .
git commit -m "init: AI-powered tech blog"
git remote add origin https://github.com/your-username/your-username.github.io.git
git push -u origin main
```

> **Important**: The repo MUST be named `your-username.github.io` for GitHub Pages to work with a custom domain. Or you can use any repo name and enable Pages from Settings.

### 2. Enable GitHub Pages

- Go to repo **Settings → Pages**
- Under "Build and deployment", select **GitHub Actions**

### 3. Add DeepSeek API Key as Secret

- Go to **Settings → Secrets and variables → Actions**
- Click **New repository secret**
- Name: `DEEPSEEK_API_KEY`
- Value: your DeepSeek API key

### 4. Run the Workflow Manually (Test)

- Go to **Actions → 🤖 Auto Blog → Run workflow**
- Set count to `1` and run

This will:
1. Generate 1 AI blog post
2. Build the static site with Hexo
3. Deploy to GitHub Pages

**After that, the bot runs automatically at 08:00 UTC daily.**

---

## 📋 What You Get After Setup

| Item | Status |
|------|--------|
| ✅ Daily AI-generated tech posts (English) | Automated |
| ✅ GitHub Pages hosting (free, fast globally) | Automated |
| ✅ Google-friendly SEO (sitemap, meta tags) | Built-in |
| ✅ No server costs | $0/month |
| ✅ No manual work after setup | True hands-off |

---

## 🧠 How the AI Content Pipeline Works

```
                       ┌──────────────┐
                       │  Topic Bank  │
                       │  (50 topics) │
                       └──────┬───────┘
                              │
                    ┌─────────▼──────────┐
                    │  DeepSeek API Call  │
                    │  (1500-2500 words)  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Save as .md Post  │
                    │  + Frontmatter SEO │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Hexo Static Build │
                    │  (HTML + CSS + JS) │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  GitHub Pages Deploy│
                    └────────────────────┘
```

### Topic Rotation

The script has a built-in topic bank of 50 SEO-optimized topics across:
- **Java & Spring Boot** (10)
- **AI & LLM Integration** (10)
- **System Design & Architecture** (10)
- **DevOps & Cloud** (10)
- **Performance & Optimization** (10)

Once all topics are used, the history resets and starts cycling again.

---

## 📈 Monetization Roadmap

### Phase 1: Content Accumulation (Month 1-3)
- Goal: 90+ published articles
- Expected traffic: 0-500 daily visitors
- Action: Apply for Google AdSense once you have 20+ quality articles

### Phase 2: Traffic Growth (Month 3-6)
- Goal: 500-5000 daily visitors
- Expected AdSense: $100-500/month
- Action: Optimize top-performing articles, interlink for better SEO

### Phase 3: Monetization Scale (Month 6+)
- Goal: 5000+ daily visitors
- Expected AdSense: $500-2000/month
- Action: Add affiliate links (AWS, DigitalOcean, hosting), promote your API service (方案五)

---

## 🔧 Local Development

```bash
# Install dependencies
npm install

# Generate a sample post (requires DEEPSEEK_API_KEY env var)
export DEEPSEEK_API_KEY=your-key-here
python generator/generate_posts.py --count 1

# Build site
npm run build

# Preview locally
npm run server
# Visit http://localhost:4000
```

---

## 📊 Monitoring

- **Traffic**: Google Analytics / Google Search Console
- **AdSense Earnings**: Google AdSense dashboard
- **CI/CD Status**: GitHub Actions → Workflows tab
- **Content Audit**: Search Console → Performance → Queries

---

## 💡 Pro Tips

1. **Custom Domain**: Buy a domain ($10/year) and set it in GitHub Pages settings for better SEO
2. **Cloudflare CDN**: Point your domain to Cloudflare for free DDoS protection and faster global delivery
3. **Interlinking**: Manually add 1-2 internal links per post for SEO juice
4. **Google Search Console**: Submit your sitemap at `yourdomain.com/sitemap.xml`
5. **Update Topic Bank**: Edit `generator/generate_posts.py` → `TOPICS` list to add trending topics

---

## 🤝 From Here: Transition to 方案五

Once this blog is running on autopilot (month 2-3), the traffic and audience become the perfect launchpad for **方案五 (AI API Aggregation Service)**:

- Blog readers → potential API service customers
- Content SEO → discovery channel for your SaaS
- Java developer audience → perfect fit for your Spring Boot Starter product

---

> Built with ❤️ and 🤖 by DevTech. Questions? Open an issue!
