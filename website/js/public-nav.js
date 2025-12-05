// Public navigation for blog and marketing pages
function renderPublicNav(activePage = '') {
    return `
    <nav class="sticky top-0 z-50 bg-slate-900/95 backdrop-blur-md border-b border-slate-800">
        <div class="container mx-auto px-6 py-4 max-w-7xl">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <a href="/" class="flex items-center gap-3 group">
                        <div class="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center group-hover:scale-105 transition">
                            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                            </svg>
                        </div>
                        <span class="text-xl font-bold">MarketDly</span>
                    </a>
                    <div class="hidden md:flex gap-1">
                        <a href="/" class="px-4 py-2 rounded-lg ${activePage === 'home' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Home</a>
                        <a href="/blog.html" class="px-4 py-2 rounded-lg ${activePage === 'blog' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Blog</a>
                        <a href="/tools.html" class="px-4 py-2 rounded-lg ${activePage === 'tools' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Tools</a>
                        <a href="/pricing.html" class="px-4 py-2 rounded-lg ${activePage === 'pricing' ? 'bg-slate-800 text-white' : 'text-gray-400 hover:text-white hover:bg-slate-800/50'} transition">Pricing</a>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <a href="/dashboard.html" class="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg font-semibold transition">
                        Sign In
                    </a>
                </div>
            </div>
        </div>
    </nav>`;
}

// Insert nav at page load
document.addEventListener('DOMContentLoaded', () => {
    const navContainer = document.getElementById('publicNav');
    if (navContainer) {
        navContainer.innerHTML = renderPublicNav(navContainer.dataset.active || '');
    }
});
