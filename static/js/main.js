// Main JavaScript for Smart E-Learn Platform

$(document).ready(function() {
    // Initialize all components
    initializeNavigation();
    initializeModals();
    initializeNotifications();
    initializeAnimations();
    initializeTooltips();
});

// Navigation Functions
function initializeNavigation() {
    // Smooth scrolling for anchor links
    $('a[href^="#"]').on('click', function(e) {
        e.preventDefault();
        const target = $(this.getAttribute('href'));
        if (target.length) {
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 1000);
        }
    });

    // Navbar scroll effect
    $(window).scroll(function() {
        if ($(window).scrollTop() > 50) {
            $('.navbar').addClass('scrolled');
        } else {
            $('.navbar').removeClass('scrolled');
        }
    });
}

// Modal Functions
function initializeModals() {
    // Login form handling
    $('#loginBtn').on('click', function() {
        const username = $('#loginUsername').val();
        const password = $('#loginPassword').val();
        
        if (!username || !password) {
            showAlert('Please fill in all fields', 'warning');
            return;
        }
        
        loginUser(username, password);
    });
    
    // Register form handling
    $('#registerBtn').on('click', function() {
        const formData = {
            first_name: $('#regFirstName').val(),
            last_name: $('#regLastName').val(),
            username: $('#regUsername').val(),
            email: $('#regEmail').val(),
            password: $('#regPassword').val(),
            confirm_password: $('#regConfirmPassword').val(),
            role: $('#regRole').val()
        };
        
        if (!validateRegistrationForm(formData)) {
            return;
        }
        
        registerUser(formData);
    });
}

// Authentication Functions
function loginUser(username, password) {
    $.ajax({
        url: '/login',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ username, password }),
        success: function(response) {
            if (response.success) {
                showAlert('Login successful!', 'success');
                setTimeout(() => {
                    window.location.href = response.redirect;
                }, 1500);
            } else {
                showAlert(response.message, 'danger');
            }
        },
        error: function() {
            showAlert('Login failed. Please try again.', 'danger');
        }
    });
}

function registerUser(formData) {
    $.ajax({
        url: '/register',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                showAlert('Registration successful! Please login.', 'success');
                $('#registerModal').modal('hide');
                $('#loginModal').modal('show');
            } else {
                showAlert(response.message, 'danger');
            }
        },
        error: function() {
            showAlert('Registration failed. Please try again.', 'danger');
        }
    });
}

function validateRegistrationForm(formData) {
    if (!formData.first_name || !formData.last_name || !formData.username || 
        !formData.email || !formData.password || !formData.confirm_password) {
        showAlert('Please fill in all fields', 'warning');
        return false;
    }
    
    if (formData.password !== formData.confirm_password) {
        showAlert('Passwords do not match', 'warning');
        return false;
    }
    
    if (formData.password.length < 6) {
        showAlert('Password must be at least 6 characters long', 'warning');
        return false;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
        showAlert('Please enter a valid email address', 'warning');
        return false;
    }
    
    return true;
}

// Notification Functions
function initializeNotifications() {
    // Load notifications on page load
    loadNotifications();
    
    // Set up notification polling
    setInterval(loadNotifications, 30000); // Check every 30 seconds
}

function loadNotifications() {
    $.get('/api/notifications', function(data) {
        updateNotificationBadge(data.length);
        updateNotificationDropdown(data);
    });
}

function updateNotificationBadge(count) {
    const badge = $('#notification-count');
    if (count > 0) {
        badge.text(count).show();
    } else {
        badge.hide();
    }
}

function updateNotificationDropdown(notifications) {
    const dropdown = $('#notification-dropdown');
    const noNotifications = $('#no-notifications');
    
    // Clear existing notifications
    dropdown.find('.notification-item').remove();
    
    if (notifications.length === 0) {
        noNotifications.show();
        return;
    }
    
    noNotifications.hide();
    
    notifications.forEach(function(notif) {
        const notificationHtml = `
            <li class="notification-item">
                <div class="d-flex align-items-start">
                    <div class="notification-icon me-3">
                        <i class="fas fa-${getNotificationIcon(notif.type)} text-${notif.type}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${notif.title}</h6>
                        <p class="text-muted small mb-0">${notif.message}</p>
                        <small class="text-muted">${formatDate(notif.created_at)}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="markNotificationRead(${notif.id})">
                        <i class="fas fa-check"></i>
                    </button>
                </div>
            </li>
        `;
        dropdown.append(notificationHtml);
    });
}

function getNotificationIcon(type) {
    const icons = {
        'info': 'info-circle',
        'success': 'check-circle',
        'warning': 'exclamation-triangle',
        'error': 'times-circle'
    };
    return icons[type] || 'bell';
}

function markNotificationRead(notificationId) {
    $.ajax({
        url: `/api/mark_notification_read/${notificationId}`,
        method: 'POST',
        success: function(response) {
            if (response.success) {
                loadNotifications(); // Reload notifications
            }
        }
    });
}

// Animation Functions
function initializeAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    $('.stat-card, .course-card, .feature-card, .testimonial-card').each(function() {
        observer.observe(this);
    });
}

// Tooltip Functions
function initializeTooltips() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Utility Functions
function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 100px; right: 20px; z-index: 9999; min-width: 300px;" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    $('body').append(alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'times-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffInMinutes < 1) {
        return 'Just now';
    } else if (diffInMinutes < 60) {
        return `${diffInMinutes} minutes ago`;
    } else if (diffInMinutes < 1440) {
        const hours = Math.floor(diffInMinutes / 60);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

// Search Functions
function initializeSearch() {
    const searchInput = $('.search-input');
    const searchResults = $('.search-results');
    
    searchInput.on('input', debounce(function() {
        const query = $(this).val();
        if (query.length > 2) {
            performSearch(query);
        } else {
            searchResults.hide();
        }
    }, 300));
}

function performSearch(query) {
    $.ajax({
        url: '/api/search',
        method: 'GET',
        data: { q: query },
        success: function(data) {
            displaySearchResults(data);
        }
    });
}

function displaySearchResults(results) {
    const searchResults = $('.search-results');
    searchResults.empty();
    
    if (results.length === 0) {
        searchResults.html('<div class="p-3 text-muted">No results found</div>');
    } else {
        results.forEach(function(result) {
            const resultHtml = `
                <div class="search-result-item p-3 border-bottom">
                    <h6 class="mb-1">${result.title}</h6>
                    <p class="text-muted small mb-0">${result.description}</p>
                    <small class="text-primary">${result.type}</small>
                </div>
            `;
            searchResults.append(resultHtml);
        });
    }
    
    searchResults.show();
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Progress Tracking Functions
function trackProgress(elementId, progress) {
    const element = $(elementId);
    const progressBar = element.find('.progress-bar');
    
    progressBar.css('width', progress + '%');
    progressBar.attr('aria-valuenow', progress);
    
    // Add animation class
    progressBar.addClass('progress-animated');
    
    setTimeout(() => {
        progressBar.removeClass('progress-animated');
    }, 1000);
}

// Course Enrollment Functions
function enrollInCourse(courseId) {
    $.ajax({
        url: `/enroll/${courseId}`,
        method: 'POST',
        contentType: 'application/json',
        success: function(response) {
            if (response.success) {
                showAlert('Successfully enrolled in course!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                showAlert(response.message, 'danger');
            }
        },
        error: function() {
            showAlert('Error enrolling in course', 'danger');
        }
    });
}

// Quiz Functions
function startQuiz(quizId) {
    // Implementation for starting a quiz
    console.log('Starting quiz:', quizId);
}

function submitQuiz(quizId, answers) {
    $.ajax({
        url: `/submit_quiz/${quizId}`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ answers: answers }),
        success: function(response) {
            if (response.success) {
                showQuizResults(response);
            } else {
                showAlert('Error submitting quiz', 'danger');
            }
        },
        error: function() {
            showAlert('Error submitting quiz', 'danger');
        }
    });
}

function showQuizResults(result) {
    // Implementation for showing quiz results
    console.log('Quiz results:', result);
}

// AI Chat Functions
function sendAIMessage(message, context) {
    $.ajax({
        url: '/api/ai-chat',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            message: message,
            context: context
        }),
        success: function(response) {
            displayAIResponse(response.answer);
        },
        error: function() {
            displayAIResponse('Sorry, I encountered an error. Please try again.');
        }
    });
}

function displayAIResponse(response) {
    // Implementation for displaying AI responses
    console.log('AI Response:', response);
}

// Export functions for global access
window.SmartElearn = {
    showAlert,
    formatDate,
    enrollInCourse,
    startQuiz,
    submitQuiz,
    sendAIMessage,
    trackProgress
};
