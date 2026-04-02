// Mobile Filter Handler for Quizzo and Pool Bar Maps

class MobileFilterManager {
  constructor(config) {
    this.mapType = config.mapType; // 'quizzo' or 'pool'
    this.filterBtn = config.filterBtn;
    this.modal = config.modal;
    this.closeBtn = config.closeBtn;
    this.applyBtn = config.applyBtn;
    this.resetBtn = config.resetBtn;
    this.filterState = config.initialState || {};
    this.onApply = config.onApply || (() => {});
    this.onReset = config.onReset || (() => {});
    
    this.init();
  }

  init() {
    // Event listeners
    this.filterBtn?.addEventListener('click', () => this.openModal());
    this.closeBtn?.addEventListener('click', () => this.closeModal());
    this.applyBtn?.addEventListener('click', () => this.apply());
    this.resetBtn?.addEventListener('click', () => this.reset());

    // Close on background click
    this.modal?.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.closeModal();
      }
    });
  }

  openModal() {
    this.modal?.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  closeModal() {
    this.modal?.classList.remove('active');
    document.body.style.overflow = '';
  }

  apply() {
    this.updateFilterState();
    this.onApply(this.filterState);
    this.closeModal();
  }

  reset() {
    // Reset UI
    this.modal?.querySelectorAll('.mobile-filter-btn-option.active').forEach(btn => {
      btn.classList.remove('active');
    });
    this.modal?.querySelectorAll('.mobile-filter-toggle.active').forEach(toggle => {
      toggle.classList.remove('active');
      toggle.querySelector('.toggle-switch').classList.remove('active');
    });
    this.modal?.querySelectorAll('select').forEach(select => {
      select.value = '';
    });

    // Reset state and apply
    this.filterState = {};
    this.onReset(this.filterState);
    this.closeModal();
  }

  updateFilterState() {
    this.filterState = {};
    
    // Get active button options (only one per section)
    this.modal?.querySelectorAll('.mobile-filter-buttons').forEach(container => {
      const activeBtn = container.querySelector('.mobile-filter-btn-option.active');
      if (activeBtn) {
        const value = activeBtn.dataset.value;
        if (value && value !== 'All') {
          const section = container.closest('.mobile-filter-section');
          const titleEl = section?.querySelector('.mobile-filter-section-title');
          const title = titleEl?.textContent.toLowerCase().trim();
          
          if (title) {
            this.filterState[title] = value;
          }
        }
      }
    });

    // Get select values
    this.modal?.querySelectorAll('select').forEach(select => {
      if (select.value) {
        const section = select.closest('.mobile-filter-section');
        const title = section?.querySelector('.mobile-filter-section-title')?.textContent.toLowerCase();
        if (title) {
          this.filterState[title] = select.value;
        }
      }
    });
  }

  addButtonListeners(selector) {
    this.modal?.querySelectorAll(selector).forEach(btn => {
      btn.addEventListener('click', (e) => {
        const container = btn.closest('.mobile-filter-buttons');
        const value = btn.dataset.value;
        
        // Single selection per category - clicking same button deselects it
        const currentActive = container?.querySelector('.mobile-filter-btn-option.active');
        
        if (currentActive === btn) {
          // Clicking active button deselects it
          btn.classList.remove('active');
        } else {
          // Deselect others and select this one
          container?.querySelectorAll('.mobile-filter-btn-option').forEach(b => {
            b.classList.remove('active');
          });
          
          // Only activate if not "All", or always activate "All"
          if (value === 'All' || currentActive?.dataset.value === 'All') {
            btn.classList.add('active');
          } else if (value !== 'All') {
            btn.classList.add('active');
          }
        }
      });
    });
  }

  addSelectListener(selector) {
    const select = this.modal?.querySelector(selector);
    if (select) {
      select.addEventListener('change', () => {
        // Can add visual feedback here if needed
      });
    }
  }
}

// Initialize Quizzo Mobile Filters
function initQuizzoMobileFilters() {
  const quizzoManager = new MobileFilterManager({
    mapType: 'quizzo',
    filterBtn: document.getElementById('quizzo-mobile-filter-btn'),
    modal: document.getElementById('quizzo-mobile-filter-modal'),
    closeBtn: document.getElementById('quizzo-filter-close'),
    applyBtn: document.getElementById('quizzo-mobile-filter-apply'),
    resetBtn: document.getElementById('quizzo-mobile-filter-reset'),
    onApply: (state) => applyQuizzoFiltersFromMobile(state),
    onReset: (state) => resetQuizzoFiltersFromMobile(state)
  });

  // Add button listeners
  quizzoManager.addButtonListeners('.mobile-filter-btn-option');
  quizzoManager.addSelectListener('#mobile-time-select');
  quizzoManager.addSelectListener('#mobile-neighborhood-select');

  window.quizzoMobileFilterManager = quizzoManager;
}

// Initialize Pool Mobile Filters
function initPoolMobileFilters() {
  const poolManager = new MobileFilterManager({
    mapType: 'pool',
    filterBtn: document.getElementById('pool-mobile-filter-btn'),
    modal: document.getElementById('pool-mobile-filter-modal'),
    closeBtn: document.getElementById('pool-filter-close'),
    applyBtn: document.getElementById('pool-mobile-filter-apply'),
    resetBtn: document.getElementById('pool-mobile-filter-reset'),
    onApply: (state) => applyPoolFiltersFromMobile(state),
    onReset: (state) => resetPoolFiltersFromMobile(state)
  });

  // Add button listeners
  poolManager.addButtonListeners('.mobile-filter-btn-option');
  poolManager.addSelectListener('#mobile-pool-cost-select');
  poolManager.addSelectListener('#mobile-pool-neighborhood-select');

  window.poolMobileFilterManager = poolManager;
}

// Quizzo filter functions (integrated with existing system)
function applyQuizzoFiltersFromMobile(filterState) {
  console.log('Applying Quizzo filters:', filterState);
  
  // Update activeFilters based on mobile filter state
  if (typeof activeFilters !== 'undefined') {
    activeFilters.weekday = filterState.weekday || null;
    activeFilters.time = filterState['start time'] || null;
    activeFilters.prizeAmount = filterState['prize amount'] ? parseFloat(filterState['prize amount']) : null;
    
    // Handle neighborhoods
    if (activeFilters.neighborhoods) {
      activeFilters.neighborhoods.clear();
      if (filterState.neighborhood) {
        activeFilters.neighborhoods.add(filterState.neighborhood);
      }
    }
    
    // Apply the filters
    if (typeof applyFilters === 'function') {
      applyFilters();
    }
  }
}

function resetQuizzoFiltersFromMobile(filterState) {
  console.log('Resetting Quizzo filters');
  if (typeof activeFilters !== 'undefined') {
    activeFilters.weekday = null;
    activeFilters.time = null;
    activeFilters.prizeAmount = null;
    activeFilters.firstPrize = null;
    if (activeFilters.neighborhoods) {
      activeFilters.neighborhoods.clear();
    }
    
    if (typeof applyFilters === 'function') {
      applyFilters();
    }
  }
}

// Pool filter functions (integrated with existing system)
function applyPoolFiltersFromMobile(filterState) {
  console.log('Applying Pool filters:', filterState);
  
  if (typeof poolActiveFilters !== 'undefined') {
    poolActiveFilters.paymentModel = filterState['payment type'] || null;
    poolActiveFilters.minTables = filterState['number of tables'] ? parseInt(filterState['number of tables']) : null;
    poolActiveFilters.priceRange = filterState['price range'] || null;
    
    // Handle neighborhoods
    if (!poolActiveFilters.neighborhoods) {
      poolActiveFilters.neighborhoods = new Set();
    }
    poolActiveFilters.neighborhoods.clear();
    if (filterState.neighborhood) {
      poolActiveFilters.neighborhoods.add(filterState.neighborhood);
    }
    
    // Apply the filters
    if (typeof applyPoolFilters === 'function') {
      applyPoolFilters();
    }
  }
}

function resetPoolFiltersFromMobile(filterState) {
  console.log('Resetting Pool filters');
  if (typeof poolActiveFilters !== 'undefined') {
    poolActiveFilters.paymentModel = null;
    poolActiveFilters.minTables = null;
    poolActiveFilters.priceRange = null;
    poolActiveFilters.hasHappyHour = false;
    poolActiveFilters.hasLeague = false;
    
    if (poolActiveFilters.neighborhoods) {
      poolActiveFilters.neighborhoods.clear();
    }
    
    if (typeof applyPoolFilters === 'function') {
      applyPoolFilters();
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Delay initialization to ensure other scripts are loaded
  setTimeout(() => {
    initQuizzoMobileFilters();
    initPoolMobileFilters();
  }, 500);
});

// Function to populate Quizzo mobile filter options
window.populateQuizzoMobileFilterOptions = function(options) {
  console.log('Populating Quizzo mobile filters:', options);
  
  // Populate Start Time dropdown
  if (options.times && options.times.length > 0) {
    const timeSelect = document.getElementById('mobile-time-select');
    if (timeSelect) {
      timeSelect.innerHTML = '<option value="">All Times</option>';
      options.times.forEach(time => {
        const option = document.createElement('option');
        option.value = time;
        option.textContent = time;
        timeSelect.appendChild(option);
      });
    }
  }

  // Populate Prize Amount
  if (options.prizeAmounts && options.prizeAmounts.length > 0) {
    const prizeAmountContainer = document.getElementById('mobile-prize-amount-buttons');
    if (prizeAmountContainer) {
      prizeAmountContainer.innerHTML = '<button class="mobile-filter-btn-option" data-value="All">All</button>';
      options.prizeAmounts.forEach(amount => {
        const btn = document.createElement('button');
        btn.className = 'mobile-filter-btn-option';
        btn.dataset.value = amount;
        btn.textContent = `$${amount}`;
        prizeAmountContainer.appendChild(btn);
      });
      // Re-add button listeners
      if (window.quizzoMobileFilterManager) {
        window.quizzoMobileFilterManager.addButtonListeners('.mobile-filter-btn-option');
      }
    }
  }

  // Populate Neighborhoods
  if (options.neighborhoods && options.neighborhoods.length > 0) {
    const neighborhoodSelect = document.getElementById('mobile-neighborhood-select');
    if (neighborhoodSelect) {
      neighborhoodSelect.innerHTML = '<option value="">All Neighborhoods</option>';
      options.neighborhoods.forEach(neighborhood => {
        const option = document.createElement('option');
        option.value = neighborhood;
        option.textContent = neighborhood;
        neighborhoodSelect.appendChild(option);
      });
    }
  }
};

// Function to populate Pool Bar mobile filter options
window.populatePoolMobileFilterOptions = function(options) {
  console.log('Populating Pool mobile filters:', options);

  // Populate Payment Types
  if (options.paymentModels && options.paymentModels.length > 0) {
    const paymentContainer = document.getElementById('mobile-pool-payment-buttons');
    if (paymentContainer) {
      paymentContainer.innerHTML = '<button class="mobile-filter-btn-option" data-value="All">All</button>';
      options.paymentModels.forEach(model => {
        const btn = document.createElement('button');
        btn.className = 'mobile-filter-btn-option';
        btn.dataset.value = model;
        btn.textContent = model;
        paymentContainer.appendChild(btn);
      });
      // Re-add button listeners
      if (window.poolMobileFilterManager) {
        window.poolMobileFilterManager.addButtonListeners('.mobile-filter-btn-option');
      }
    }
  }

  // Populate Cost/Price filter
  if (options.costRanges && options.costRanges.length > 0) {
    const costSelect = document.getElementById('mobile-pool-cost-select');
    if (costSelect) {
      costSelect.innerHTML = '<option value="">All Prices</option>';
      options.costRanges.forEach(range => {
        const option = document.createElement('option');
        option.value = range;
        option.textContent = range;
        costSelect.appendChild(option);
      });
    }
  }

  // Populate Neighborhoods
  if (options.neighborhoods && options.neighborhoods.length > 0) {
    const neighborhoodSelect = document.getElementById('mobile-pool-neighborhood-select');
    if (neighborhoodSelect) {
      neighborhoodSelect.innerHTML = '<option value="">All Neighborhoods</option>';
      options.neighborhoods.forEach(neighborhood => {
        const option = document.createElement('option');
        option.value = neighborhood;
        option.textContent = neighborhood;
        neighborhoodSelect.appendChild(option);
      });
    }
  }
};
