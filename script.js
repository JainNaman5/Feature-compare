const form = document.getElementById('compare-form');
const url1Input = document.getElementById('url1');
const url2Input = document.getElementById('url2');
const loadingIndicator = document.getElementById('loading-indicator');
const resultsSection = document.getElementById('comparison-results');
const tableHeaders = document.getElementById('table-headers');
const tableBody = document.getElementById('comparison-table-body');
const modal = document.getElementById('modal');
const modalMessage = document.getElementById('modal-message');
const modalCloseBtn = document.getElementById('modal-close-btn');

// Configuration - change this to your backend URL
const API_BASE_URL = 'https://feature-compare.onrender.com';

// Function to show the custom modal
function showModal(message) {
    modalMessage.textContent = message;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

// Function to close the modal
modalCloseBtn.addEventListener('click', () => {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
});

// Close modal when clicking outside of it
modal.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
    }
});

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const url1 = url1Input.value.trim();
    const url2 = url2Input.value.trim();

    if (!url1 || !url2) {
        showModal('Please enter both URLs to compare.');
        return;
    }

    // Validate URLs
    if (!isValidUrl(url1) || !isValidUrl(url2)) {
        showModal('Please enter valid URLs (must start with http:// or https://).');
        return;
    }

    // Show loading spinner and hide previous results
    loadingIndicator.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    tableBody.innerHTML = '';
    tableHeaders.innerHTML = `<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Feature</th>`;

    try {
        // Real API call to Python backend
        const response = await fetch(`${API_BASE_URL}/compare`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url1, url2 })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            showModal(data.error || 'An error occurred while processing the request.');
        } else {
            displayResults(data);
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        
        // Fallback to simulation if backend is not available
        if (error.message.includes('fetch')) {
            console.log('Backend not available, falling back to simulation...');
            showModal('Backend server not available. Using demo data instead.');
            
            // Simulate delay and show demo data
            setTimeout(() => {
                const dummyData = simulatePythonResponse(url1, url2);
                if (dummyData.error) {
                    showModal(dummyData.error);
                } else {
                    displayResults(dummyData);
                }
            }, 1000);
        } else {
            showModal('A network error occurred. Please check your connection and try again.');
        }
    } finally {
        loadingIndicator.classList.add('hidden');
    }
});

// URL validation function
function isValidUrl(string) {
    try {
        new URL(string);
        return string.startsWith('http://') || string.startsWith('https://');
    } catch (_) {
        return false;
    }
}

// Simulates the JSON response from a Python backend (fallback for demo)
function simulatePythonResponse(url1, url2) {
    const productA = {
        'Product': 'Smartphone X',
        'Screen Size': '6.1 inches',
        'Processor': 'A15 Bionic',
        'Storage': '256GB',
        'Camera': '12MP Wide, 12MP Ultra-Wide',
        'Color': 'Midnight Black',
        'Weight': '173g',
        'Battery Life': 'Up to 22 hours video playback',
        'Price': '$799'
    };

    const productB = {
        'Product': 'Smartphone Y',
        'Screen Size': '6.5 inches',
        'Processor': 'Snapdragon 8 Gen 2',
        'Storage': '512GB',
        'Camera': '50MP Wide, 12MP Telephoto',
        'Color': 'Titanium Gray',
        'Weight': '195g',
        'Battery Life': 'Up to 25 hours video playback',
        'Price': '$899'
    };

    const getRandomItem = () => {
        const items = [
            { 'Product': 'Sample Item A', 'Feature 1': 'Value A1', 'Feature 2': 'Value A2', 'Feature 3': 'Value A3' },
            { 'Product': 'Sample Item B', 'Feature A': 'Value B1', 'Feature B': 'Value B2', 'Feature C': 'Value B3' },
            { 'Product': 'Demo Product', 'Key X': 'Data Y', 'Key Z': 'Data W', 'Specification': 'Demo Spec' }
        ];
        return items[Math.floor(Math.random() * items.length)];
    };

    const isProduct = url1.includes('product') || url2.includes('product');
    const data1 = isProduct ? productA : getRandomItem();
    const data2 = isProduct ? productB : getRandomItem();

    if (url1.includes('error') || url2.includes('error')) {
        return { error: 'Simulated API Error: Failed to scrape one of the URLs. Please check and try again.' };
    }

    return { data1: data1, data2: data2 };
}



function displayResults(data) {
    resultsSection.classList.remove('hidden');
    showJsonOutput(data);

    const allFeatures = new Set([
        ...Object.keys(data.data1),
        ...Object.keys(data.data2)
    ]);

    tableHeaders.innerHTML = `
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Feature</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${data.data1['Product'] || 'Item 1'}</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">${data.data2['Product'] || 'Item 2'}</th>
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Feature Name</th>
    `;

    allFeatures.forEach(feature => {
        if (feature === 'Product') return;

        const value1 = data.data1[feature] || 'N/A';
        const value2 = data.data2[feature] || 'N/A';
        const isDifferent = value1 !== value2;
        const cellClass = isDifferent ? 'text-gray-900' : 'text-gray-500';

        const row = document.createElement('tr');
        row.classList.add('hover:bg-gray-50', 'transition-colors', 'duration-200');

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${feature}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm ${cellClass}">${value1}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm ${cellClass}">${value2}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600">${feature}</td>
        `;

        tableBody.appendChild(row);
    });

    resultsSection.scrollIntoView({ behavior: 'smooth' });
}





