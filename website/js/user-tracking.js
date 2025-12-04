// User tracking and subscription utilities

function getUserId() {
    let userId = localStorage.getItem('user_id');
    if (!userId) {
        userId = 'anon_' + Math.random().toString(36).substr(2, 9) + Date.now();
        localStorage.setItem('user_id', userId);
    }
    return userId;
}

function showUpgradeModal(usage, limit) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4';
    modal.innerHTML = `
        <div class="bg-slate-800 rounded-2xl p-8 max-w-md w-full border border-blue-500">
            <h2 class="text-2xl font-bold mb-4 text-white">Daily Limit Reached</h2>
            <p class="text-gray-300 mb-6">
                You've used ${usage} of ${limit} free ticker analyses today. 
                Upgrade to Basic for unlimited access!
            </p>
            <div class="space-y-3">
                <a href="/pricing.html" class="block w-full text-center py-3 px-6 bg-blue-600 hover:bg-blue-500 rounded-lg transition font-bold text-white">
                    View Pricing
                </a>
                <button onclick="this.closest('.fixed').remove()" class="block w-full text-center py-3 px-6 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-white">
                    Close
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

async function checkAndAnalyzeTicker(ticker) {
    const userId = getUserId();
    
    try {
        const response = await fetch('https://xfi2u4ajm9.execute-api.us-east-1.amazonaws.com/prod/ticker-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker, user_id: userId })
        });
        
        if (response.status === 429) {
            const data = await response.json();
            showUpgradeModal(data.usage, data.limit);
            return null;
        }
        
        if (!response.ok) {
            throw new Error('Failed to analyze ticker');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error analyzing ticker:', error);
        throw error;
    }
}
