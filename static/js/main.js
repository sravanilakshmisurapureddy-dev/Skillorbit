/**
 * Campus2Career AI - Main Client Interactions
 */

// Modal Management
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
}

// Close modal when clicking on overlay background
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
});

// Tab Navigation
function switchTab(tabId, tabBtn) {
  // Hide all tab panes in this container
  const parent = tabBtn.closest('.tabs-wrapper') || document;
  const panes = parent.querySelectorAll('.tab-pane');
  const buttons = parent.querySelectorAll('.tab-btn');

  panes.forEach(p => p.classList.remove('active'));
  buttons.forEach(b => b.classList.remove('active'));

  const activePane = document.getElementById(tabId);
  if (activePane) activePane.classList.add('active');
  if (tabBtn) tabBtn.classList.add('active');
}

// AJAX Shortlist Toggle for Company Dashboard
function toggleShortlist(studentId, btnElement) {
  const formData = new FormData();
  formData.append('student_id', studentId);

  fetch('/company/shortlist/toggle', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      if (data.is_shortlisted) {
        btnElement.classList.add('shortlisted');
        btnElement.innerHTML = '★ Shortlisted';
        btnElement.style.color = '#fbbf24';
      } else {
        btnElement.classList.remove('shortlisted');
        btnElement.innerHTML = '☆ Shortlist';
        btnElement.style.color = 'inherit';
      }
    }
  })
  .catch(err => console.error('Shortlist toggle error:', err));
}

// Auto Dismiss Alerts after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });
});
