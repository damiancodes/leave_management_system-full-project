// Admin Dashboard JavaScript Enhancements
// Compatible with existing CSS styles

document.addEventListener('DOMContentLoaded', function() {
    // Add classes to existing elements for our new styling
    addCustomClasses();

    // Initialize counter animations for stats
    initCounters();

    // Add hover effects to admin actions
    initActionHoverEffects();

    // Initialize tooltips if Bootstrap JS is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Add our custom classes to existing elements
function addCustomClasses() {
    // Add dashboard-header class to the first row
    const headerRow = document.querySelector('.row:first-child');
    if (headerRow) {
        headerRow.classList.add('dashboard-header');
    }

    // Use jQuery to find elements by text content
    // Add admin-actions class to the actions card
    jQuery('.card-header:contains("Admin Actions")').closest('.card').addClass('admin-actions');

    // Add setup-required class to the setup card
    jQuery('.card-header:contains("Setup Required")').closest('.card').addClass('setup-required');

    // Add stats-card class to all stat cards in the Quick Stats section
    const statsHeader = jQuery('.card-header:contains("Quick Stats")');
    if (statsHeader.length) {
        const statsSection = statsHeader.closest('.card');
        statsSection.find('.card').each(function() {
            jQuery(this).addClass('stats-card');
            // Add counter-value class to the stat values
            const statValue = jQuery(this).find('h3');
            if (statValue.length) {
                statValue.addClass('counter-value');
            }
        });
    }
}

// Add :contains selector functionality
if (!Element.prototype.matches) {
    Element.prototype.matches = Element.prototype.msMatchesSelector || Element.prototype.webkitMatchesSelector;
}

if (!Element.prototype.closest) {
    Element.prototype.closest = function(s) {
        var el = this;
        do {
            if (el.matches(s)) return el;
            el = el.parentElement || el.parentNode;
        } while (el !== null && el.nodeType === 1);
        return null;
    };
}

// Custom contains selector
jQuery.expr[':'].contains = function(a, i, m) {
    return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
};

// Counter animation for stats
function initCounters() {
    document.querySelectorAll('.counter-value').forEach(function(counterElement) {
        const target = parseInt(counterElement.textContent.replace(/,/g, ''));
        const duration = 1500; // Animation duration in milliseconds
        const increment = target / (duration / 16); // 60 fps

        let current = 0;
        const counterInterval = setInterval(function() {
            current += increment;

            if (current >= target) {
                counterElement.textContent = target;
                clearInterval(counterInterval);
            } else {
                counterElement.textContent = Math.round(current);
            }
        }, 16);
    });
}

// Hover effects for action items
function initActionHoverEffects() {
    const actionItems = document.querySelectorAll('.admin-actions .list-group-item');

    actionItems.forEach(item => {
        // Create and add tooltip data attributes
        item.setAttribute('data-bs-toggle', 'tooltip');
        item.setAttribute('data-bs-placement', 'right');
        item.setAttribute('title', 'Click to access');

        // Add ripple effect on click
        item.addEventListener('click', function(e) {
            // Create ripple element
            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');
            this.appendChild(ripple);

            // Position the ripple where clicked
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = e.clientX - rect.left - size/2 + 'px';
            ripple.style.top = e.clientY - rect.top - size/2 + 'px';

            // Remove ripple after animation completes
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// Add ripple effect CSS dynamically
function addRippleStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .ripple-effect {
            position: absolute;
            border-radius: 50%;
            background-color: rgba(0, 0, 0, 0.1);
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        }
        
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .list-group-item {
            position: relative;
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);
}

// Call to add ripple styles
addRippleStyles();