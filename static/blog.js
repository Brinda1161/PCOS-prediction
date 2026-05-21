document.addEventListener('DOMContentLoaded', function() {
            const submitAdviceBtn = document.getElementById('submit-advice');
            const adviceContainer = document.getElementById('advice-container');
            
            submitAdviceBtn.addEventListener('click', function() {
                const name = document.getElementById('user-name').value || 'Anonymous';
                const adviceText = document.getElementById('user-advice').value;
                
                if (!adviceText.trim()) {
                    alert('Please share your advice before submitting.');
                    return;
                }
                
                const adviceDiv = document.createElement('div');
                adviceDiv.className = 'user-advice';
                adviceDiv.innerHTML = `
                    <h4>${name}</h4>
                    <p>"${adviceText}"</p>
                `;
                
                // Add to the top of the container
                adviceContainer.insertBefore(adviceDiv, adviceContainer.firstChild);
                
                // Clear the form
                document.getElementById('user-name').value = '';
                document.getElementById('user-advice').value = '';
                
                // Show confirmation
                alert('Thank you for sharing your advice!');
            });
        });