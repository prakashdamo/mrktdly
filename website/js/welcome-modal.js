// Show welcome modal on first login for free users

function checkAndShowWelcome() {
    const hasSeenWelcome = localStorage.getItem('hasSeenWelcome');
    const userEmail = localStorage.getItem('userEmail');
    
    if (!hasSeenWelcome && userEmail) {
        // Check subscription tier
        checkUserTier(userEmail).then(tier => {
            if (tier === 'free') {
                showWelcomeModal();
                localStorage.setItem('hasSeenWelcome', 'true');
            }
        });
    }
}

async function checkUserTier(email) {
    try {
        const response = await fetch('https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/subscription-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: email, action: 'check' })
        });
        const data = await response.json();
        return data.tier || 'free';
    } catch (error) {
        console.error('Error checking tier:', error);
        return 'free';
    }
}

function showWelcomeModal() {
    const modal = document.createElement('div');
    modal.id = 'welcomeModal';
    modal.className = 'fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4';
    modal.innerHTML = `
        <div class="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 max-w-2xl w-full border-2 border-blue-500 relative">
            <button onclick="document.getElementById('welcomeModal').remove()" class="absolute top-4 right-4 text-gray-400 hover:text-white text-2xl">×</button>
            
            <div class="text-center mb-6">
                <div class="text-6xl mb-4">🎉</div>
                <h2 class="text-3xl font-bold mb-2 text-white">Welcome to MarketDly!</h2>
                <p class="text-gray-300">You're on the Free plan. Here's what you can do:</p>
            </div>
            
            <div class="grid md:grid-cols-2 gap-6 mb-6">
                <div class="bg-slate-700/50 rounded-lg p-4">
                    <h3 class="font-bold text-green-400 mb-3">✓ Free Plan Includes:</h3>
                    <ul class="space-y-2 text-sm text-gray-300">
                        <li>• 3 ticker analyses per day</li>
                        <li>• 3 sample trade signals</li>
                        <li>• Daily market summary</li>
                        <li>• Market intelligence charts</li>
                    </ul>
                </div>
                
                <div class="bg-gradient-to-br from-blue-900/50 to-purple-900/50 rounded-lg p-4 border border-blue-500">
                    <h3 class="font-bold text-blue-400 mb-3">🚀 Upgrade to Pro ($29/mo):</h3>
                    <ul class="space-y-2 text-sm text-gray-300">
                        <li>• <strong>Unlimited</strong> ticker analyses</li>
                        <li>• <strong>All</strong> trade signals</li>
                        <li>• 2x daily email alerts</li>
                        <li>• Performance tracking</li>
                        <li>• Portfolio management</li>
                    </ul>
                </div>
            </div>
            
            <div class="flex gap-4">
                <button onclick="window.location.href='/pricing.html'" class="flex-1 py-3 px-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg font-bold text-white transition">
                    Upgrade to Pro →
                </button>
                <button onclick="document.getElementById('welcomeModal').remove()" class="flex-1 py-3 px-6 bg-slate-700 hover:bg-slate-600 rounded-lg font-bold text-white transition">
                    Continue with Free
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Auto-run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkAndShowWelcome);
} else {
    checkAndShowWelcome();
}
