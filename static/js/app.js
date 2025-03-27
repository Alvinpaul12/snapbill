let items = [];
let people = [];

// Add Item
document.getElementById('addItem').addEventListener('click', () => {
    const name = document.getElementById('itemName').value.trim();
    const price = parseFloat(document.getElementById('itemPrice').value);
    const quantity = parseInt(document.getElementById('itemQuantity').value) || 1;

    if (name && price) {
        items.push({
            name,
            price,
            quantity,
            assigned_to: []
        });
        updateItemList();
        updateAssignments();
        clearInputs();
    }
});

// Add Person
document.getElementById('addPerson').addEventListener('click', () => {
    const name = document.getElementById('personName').value.trim();
    if (name && !people.includes(name)) {
        people.push(name);
        updatePeopleList();
        updateAssignments();
        document.getElementById('personName').value = '';
    }
});

document.getElementById('scanBtn').addEventListener('click', async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    const uploadStatus = document.getElementById('uploadStatus');
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('image', file);
        
        try {
            uploadStatus.textContent = 'Processing image...';
            uploadStatus.className = '';
            
            const response = await fetch('http://localhost:5000/scan-bill', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.items && data.items.length > 0) {
                items = [...items, ...data.items];
                updateItemList();
                uploadStatus.textContent = 'Bill processed successfully!';
                uploadStatus.className = 'success';
            } else {
                uploadStatus.textContent = 'No items found in the bill';
                uploadStatus.className = 'error';
            }
        } catch (error) {
            console.error('Error:', error);
            uploadStatus.textContent = 'Error processing the bill';
            uploadStatus.className = 'error';
        }
    };
    
    input.click();
});

// Update Item List
function updateItemList() {
    const itemList = document.getElementById('itemList');
    itemList.innerHTML = items.map((item, index) => `
        <div class="item">
            <span>${item.name} - $${item.price.toFixed(2)} x ${item.quantity}</span>
            <button class="remove-btn" onclick="removeItem(${index})">Remove</button>
        </div>
    `).join('');
    updateAssignments();
}

// Update People List
function updatePeopleList() {
    const peopleList = document.getElementById('peopleList');
    peopleList.innerHTML = people.map((person, index) => `
        <li>
            ${person}
            <button class="remove-btn" onclick="removePerson(${index})">Remove</button>
        </li>
    `).join('');
    updateAssignments();
}

// Update Assignments
function updateAssignments() {
    const assignmentsDiv = document.getElementById('assignments');
    assignmentsDiv.innerHTML = items.map((item, itemIndex) => `
        <div class="item-assignment">
            <div class="item-details">
                <p>${item.name} - $${item.price.toFixed(2)} x ${item.quantity}</p>
            </div>
            <div class="person-checkboxes">
                ${people.map(person => `
                    <label class="checkbox-label">
                        <input type="checkbox" 
                            value="${person}"
                            ${item.assigned_to.includes(person) ? 'checked' : ''}
                            onchange="updateItemAssignment(${itemIndex}, '${person}', this.checked)"
                        >
                        ${person}
                    </label>
                `).join('')}
            </div>
        </div>
    `).join('');
}

// New function to handle checkbox changes
function updateItemAssignment(itemIndex, person, isChecked) {
    if (isChecked) {
        if (!items[itemIndex].assigned_to.includes(person)) {
            items[itemIndex].assigned_to.push(person);
        }
    } else {
        items[itemIndex].assigned_to = items[itemIndex].assigned_to.filter(p => p !== person);
    }
    updateBillSummary();
}

// Assign Persons to Items
function assignPersons(itemIndex) {
    const select = document.getElementById(`select-${itemIndex}`);
    const selectedPersons = Array.from(select.selectedOptions).map(option => option.value);
    items[itemIndex].assigned_to = selectedPersons;
    updateBillSummary();
}

// Update Bill Summary with fixed calculation
function updateBillSummary() {
    const totals = {};
    people.forEach(person => totals[person] = 0);

    items.forEach(item => {
        if (item.assigned_to.length > 0) {
            const totalItemCost = item.price * item.quantity;
            const splitAmount = totalItemCost / item.assigned_to.length;
            item.assigned_to.forEach(person => {
                totals[person] += splitAmount;
            });
        }
    });

    const splitResults = document.getElementById('splitResults');
    splitResults.innerHTML = `
        <div class="split-summary">
            ${Object.entries(totals).map(([person, amount]) => `
                <div class="split-amount">
                    <strong>${person}:</strong> $${amount.toFixed(2)}
                </div>
            `).join('')}
        </div>
    `;
}

// Clear Inputs
function clearInputs() {
    document.getElementById('itemName').value = '';
    document.getElementById('itemPrice').value = '';
    document.getElementById('itemQuantity').value = '1';
}

// Initialize
document.getElementById('calculateSplit').addEventListener('click', updateBillSummary);

// Add these new functions for removing items and people
function removeItem(index) {
    items.splice(index, 1);
    updateItemList();
    updateBillSummary();
}

function removePerson(index) {
    const personToRemove = people[index];
    people.splice(index, 1);
    
    // Remove this person from all item assignments
    items.forEach(item => {
        item.assigned_to = item.assigned_to.filter(p => p !== personToRemove);
    });
    
    updatePeopleList();
    updateBillSummary();
}
