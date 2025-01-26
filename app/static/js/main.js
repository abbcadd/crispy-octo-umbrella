document.getElementById('optimizeForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const fundCodes = document.getElementById('fundCodes').value.split(',');
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    try {
        const response = await fetch('/api/optimize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fund_codes: fundCodes,
                start_date: startDate,
                end_date: endDate
            })
        });
        
        const result = await response.json();
        displayResults(result);
    } catch (error) {
        console.error('Error:', error);
    }
});

function displayResults(result) {
    const resultsDiv = document.getElementById('results');
    // 显示优化结果
    let html = '<h3>优化结果</h3>';
    html += '<table class="table">';
    html += '<tr><th>基金代码</th><th>权重</th></tr>';
    
    for (const [code, weight] of Object.entries(result.weights)) {
        html += `<tr><td>${code}</td><td>${(weight * 100).toFixed(2)}%</td></tr>`;
    }
    
    html += '</table>';
    resultsDiv.innerHTML = html;
} 