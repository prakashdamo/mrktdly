// Cognito Configuration
const COGNITO_CONFIG = {
    UserPoolId: 'us-east-1_N5yuAGHc3',
    ClientId: '3ras51lrq716j8mij5887uug17',
    Region: 'us-east-1'
};

// Check if user is authenticated (non-blocking)
function checkAuth() {
    try {
        const session = getSession();
        if (!session) {
            console.log('No session found, redirecting to home');
            setTimeout(() => window.location.href = '/index.html', 100);
            return false;
        }
        console.log('Session found, user authenticated');
        return true;
    } catch (error) {
        console.error('Auth check error:', error);
        setTimeout(() => window.location.href = '/index.html', 100);
        return false;
    }
}

// Get current session from localStorage
function getSession() {
    try {
        // Find the LastAuthUser key
        const lastAuthUserKey = `CognitoIdentityServiceProvider.${COGNITO_CONFIG.ClientId}.LastAuthUser`;
        const lastAuthUser = localStorage.getItem(lastAuthUserKey);
        
        if (!lastAuthUser) {
            console.log('No LastAuthUser found');
            console.log('Looking for key:', lastAuthUserKey);
            console.log('Available keys:', Object.keys(localStorage).filter(k => k.includes('Cognito')));
            return null;
        }
        
        const idTokenKey = `CognitoIdentityServiceProvider.${COGNITO_CONFIG.ClientId}.${lastAuthUser}.idToken`;
        const idToken = localStorage.getItem(idTokenKey);
        
        if (!idToken) {
            console.log('Missing idToken');
            console.log('Looking for key:', idTokenKey);
            console.log('Available keys:', Object.keys(localStorage).filter(k => k.includes('idToken')));
            return null;
        }
        
        console.log('Session retrieved successfully');
        console.log('Token length:', idToken.length);
        return { idToken };
    } catch (error) {
        console.error('Error getting session:', error);
        return null;
    }
}

// Authenticated fetch wrapper
async function authenticatedFetch(url, options = {}) {
    const session = getSession();
    if (!session) {
        throw new Error('Not authenticated');
    }
    
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.idToken}`,
        ...options.headers
    };
    
    console.log('Making authenticated request to:', url);
    if (session.idToken) {
        console.log('Authorization header:', session.idToken.substring(0, 50) + '...');
    }
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    console.log('Response status:', response.status);
    
    if (response.status === 401 || response.status === 403) {
        console.error('Authentication failed, clearing session');
        const errorText = await response.text();
        console.error('Error response:', errorText);
        localStorage.clear();
        window.location.href = '/index.html';
        throw new Error('Session expired');
    }
    
    if (!response.ok) {
        const errorText = await response.text();
        console.error('API error:', errorText);
        throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    return response;
}

// Logout function
function logout() {
    localStorage.clear();
    window.location.href = '/index.html';
}
