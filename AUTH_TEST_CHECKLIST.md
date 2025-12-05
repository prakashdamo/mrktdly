# Authentication Flow Test Checklist

## Test Date: December 5, 2024

---

## 🔴 BEFORE LOGIN (Unauthenticated User)

### Homepage (/)
- [ ] Visit https://marketdly.com
- [ ] Click "Sign In" in nav → Should go to /login.html
- [ ] Click "Start Learning Free" hero button → Should go to /signup.html
- [ ] Click "Get Started" on Basic tier → Should go to /signup.html
- [ ] Click "Go Pro" on Pro tier → Should go to /signup.html
- [ ] Click "Create Account" at bottom → Should go to /signup.html

### Signup Page (/signup.html)
- [ ] Visit https://marketdly.com/signup.html
- [ ] Page loads with branded design
- [ ] Form has: Name, Email, Password fields
- [ ] Terms checkbox is required
- [ ] Try submitting without terms → Should show error
- [ ] Enter valid details and submit
- [ ] Should show success message
- [ ] Should redirect to /login.html after 3 seconds
- [ ] Check email for verification code

### Login Page (/login.html)
- [ ] Visit https://marketdly.com/login.html
- [ ] Page loads with branded design
- [ ] Form has: Email, Password fields
- [ ] Try wrong password → Should show error message
- [ ] Try correct credentials → Should redirect to /dashboard.html
- [ ] "Remember me" checkbox works

### Protected Pages (Should Redirect to Home)
- [ ] Try visiting /dashboard.html without login → Redirects to /
- [ ] Try visiting /performance.html without login → Redirects to /
- [ ] Try visiting /portfolio.html without login → Redirects to /

---

## 🟢 AFTER LOGIN (Authenticated User)

### Dashboard (/dashboard.html)
- [ ] After login, lands on /dashboard.html
- [ ] Page loads without redirect loop
- [ ] Stats show: Win Rate, Active Patterns, Today's Patterns, Expectancy
- [ ] Navigation shows user menu
- [ ] Can access all dashboard features

### Navigation
- [ ] Nav bar shows "Dashboard" link
- [ ] Nav bar shows user email or name
- [ ] Logout button works
- [ ] After logout, redirects to home

### Protected Pages (Should Work)
- [ ] Can access /performance.html
- [ ] Can access /portfolio.html
- [ ] Can access /market-insights.html
- [ ] Can access /swing-scanner.html

### Session Persistence
- [ ] Close browser and reopen
- [ ] Visit /dashboard.html → Should still be logged in (if "Remember me" checked)
- [ ] Session persists across page refreshes

---

## 🔧 EDGE CASES

### Already Logged In
- [ ] While logged in, visit /login.html → Should redirect to /dashboard.html
- [ ] While logged in, visit /signup.html → Should redirect to /dashboard.html

### Email Verification
- [ ] New user tries to login before verifying email → Should show error
- [ ] After verifying email, login works

### Password Reset
- [ ] Click "Forgot password?" on login page
- [ ] Should go to /forgot-password.html (if exists)

### Invalid Sessions
- [ ] Clear localStorage
- [ ] Visit /dashboard.html → Should redirect to /

---

## ✅ SUCCESS CRITERIA

All checkboxes above should be checked for full authentication flow to be working.

---

## 🐛 ISSUES FOUND

(Document any issues here)

1. 
2. 
3. 

---

## 📝 NOTES

- Cognito User Pool: us-east-1_N5yuAGHc3
- Client ID: 3ras51lrq716j8mij5887uug17
- Test with real email address for verification
