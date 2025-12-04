// Show pricing modal after 30 seconds if not logged in

function showPricingModal() {
    // Don't show if already logged in
    if (localStorage.getItem('userEmail')) return;
    
    // Don't show if already dismissed today
    const dismissedDate = localStorage.getItem('pricingModalDismissed');
    const today = new Date().toDateString();
    if (dismissedDate === today) return;
    
    const modal = document.createElement('div');
    modal.id = 'pricingModal';
    modal.className = 'fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 animate-fade-in';
    modal.innerHTML = `
        <div class="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 max-w-4xl w-full border-2 border-blue-500 relative">
            <button onclick="dismissPricingModal()" class="absolute top-4 right-4 text-gray-400 hover:text-white text-3xl">×</button>
            
            <div class="text-center mb-8">
                <h2 class="text-3xl font-bold mb-2 text-white">Ready to Level Up Your Trading?</h2>
                <p class="text-gray-300">Choose the plan that fits your needs</p>
            </div>
            
            <div class="grid md:grid-cols-2 gap-6">
                <!-- Free Plan -->
                <div class="bg-slate-700/50 rounded-xl p-6 border border-slate-600">
                    <h3 class="text-xl font-bold mb-2">Free</h3>
                    <div class="text-3xl font-bold mb-4">$0<span class="text-sm text-gray-400">/forever</span></div>
                    <ul class="space-y-2 text-sm mb-6">
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span>Daily market summary</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span>3 ticker analyses/day</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span>3 sample signals</span>
                        </li>
                    </ul>
                    <button onclick="document.getElementById('heroSignupBtn').click(); dismissPricingModal();" class="w-full py-3 bg-slate-600 hover:bg-slate-500 rounded-lg font-bold transition">
                        Start Free
                    </button>
                </div>

                <!-- Pro Plan -->
                <div class="bg-gradient-to-br from-blue-900/70 to-purple-900/70 rounded-xl p-6 border-2 border-blue-500 relative">
                    <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 px-3 py-1 rounded-full text-xs font-bold">
                        RECOMMENDED
                    </div>
                    <h3 class="text-xl font-bold mb-2">Pro</h3>
                    <div class="text-3xl font-bold mb-4">$29<span class="text-sm text-gray-400">/month</span></div>
                    <ul class="space-y-2 text-sm mb-6">
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span><strong>Unlimited</strong> analyses</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span><strong>All</strong> trade signals</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span>2x daily email alerts</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-green-400">✓</span>
                            <span>Performance tracking</span>
                        </li>
                    </ul>
                    <button onclick="window.location.href='/pricing.html'" class="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg font-bold transition">
                        Upgrade to Pro
                    </button>
                </div>
            </div>
            
            <div class="text-center mt-6">
                <button onclick="dismissPricingModal()" class="text-gray-400 hover:text-white text-sm">
                    Maybe later
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function dismissPricingModal() {
    const modal = document.getElementById('pricingModal');
    if (modal) modal.remove();
    localStorage.setItem('pricingModalDismissed', new Date().toDateString());
}

// Show after 30 seconds
setTimeout(showPricingModal, 30000);
