// Shared navigation for authenticated pages
function renderNav(activePage = '') {
    // Get username first
    const username = localStorage.getItem(`CognitoIdentityServiceProvider.3ras51lrq716j8mij5887uug17.LastAuthUser`);
    // Then get the actual email using the username
    const userEmail = username ? 
        (localStorage.getItem(`CognitoIdentityServiceProvider.3ras51lrq716j8mij5887uug17.${username}.email`) || username) : 
        'User';
    
    return `
    <nav class="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800">
        <div class="container mx-auto px-6 py-4 max-w-7xl">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <a href="/dashboard.html" class="flex items-center gap-3 group">
                        <div class="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center group-hover:scale-105 transition">
                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                            </svg>
                        </div>
                        <span class="text-xl font-bold">MarketDly</span>
                    </a>
                    <div class="hidden md:flex gap-1">
                        <a href="/dashboard.html" class="px-4 py-2 rounded-lg ${activePage === 'dashboard' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Dashboard</a>
                        <a href="/market-insights.html" class="px-4 py-2 rounded-lg ${activePage === 'market-insights' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Market Intelligence</a>
                        <a href="/portfolio.html" class="px-4 py-2 rounded-lg ${activePage === 'portfolio' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Portfolio</a>
                        <a href="/performance.html" class="px-4 py-2 rounded-lg ${activePage === 'performance' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Performance</a>
                        <a href="/tools.html" class="px-4 py-2 rounded-lg ${activePage === 'tools' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Tools</a>
                        <a href="/blog.html" class="px-4 py-2 rounded-lg ${activePage === 'blog' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Blog</a>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span class="text-gray-400 text-sm">👋 <span class="text-white font-medium">${userEmail}</span></span>
                    <button onclick="logout()" class="px-4 py-2 text-gray-400 hover:text-white hover:bg-slate-800 rounded-lg transition">Logout</button>
                </div>
            </div>
        </div>
    </nav>`;
}

// Insert nav at page load
document.addEventListener('DOMContentLoaded', () => {
    const navContainer = document.getElementById('appNav');
    if (navContainer) {
        navContainer.innerHTML = renderNav(navContainer.dataset.active || '');
    }
});
