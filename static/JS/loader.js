const loginForm = document.getElementById('loginForm');
const loader = document.getElementById('loader');

loginForm.addEventListener('submit', function (event) {
  event.preventDefault(); // Prevent the form from submitting immediately
  
  // Show the loader
  loader.style.visibility = 'visible';
  
  // Add a 1-second delay before allowing form submission
  setTimeout(() => {
    loginForm.submit(); // Submit the form after the delay
  }, 1000);
});
