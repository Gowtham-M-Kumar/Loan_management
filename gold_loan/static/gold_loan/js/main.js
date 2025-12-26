console.log("Gold Loan static JS loaded");

document.addEventListener('DOMContentLoaded', function () {
    // ==============================
    // MOBILE SIDEBAR TOGGLE
    // ==============================
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a');

    // Toggle sidebar on menu button click
    if (menuToggle) {
        menuToggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
            document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
        });
    }

    // Close sidebar when clicking overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function () {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.style.overflow = '';
        });
    }

    // Close sidebar when clicking a link (all devices)
    sidebarLinks.forEach(function (link) {
        link.addEventListener('click', function () {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.style.overflow = '';
        });
    });

    // Handle window resize - Optional: Keep concise or remove if hindering
    // For now, we allow the drawer to stay open or we can just reset if needed, 
    // but better to remove the auto-close on desktop since desktop uses drawer too.


    // ==============================
    // DARK MODE TOGGLE
    // ==============================
    const themeToggle = document.getElementById('themeToggle');
    const themeText = document.getElementById('themeText');
    const iconMoon = document.getElementById('iconMoon');
    const iconSun = document.getElementById('iconSun');

    // Function to update UI based on theme
    function updateThemeUI(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (iconMoon) iconMoon.style.display = 'none';
            if (iconSun) iconSun.style.display = 'block';
            if (themeText) themeText.innerText = 'Light Mode';
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (iconMoon) iconMoon.style.display = 'block';
            if (iconSun) iconSun.style.display = 'none';
            if (themeText) themeText.innerText = 'Dark Mode';
            localStorage.setItem('theme', 'light');
        }
    }

    // Initialize state (UI only, variable already set by inline script)
    const currentTheme = localStorage.getItem('theme') || 'light';
    // We call this to ensure icons match the inline script state
    if (currentTheme === 'dark') {
        if (iconMoon) iconMoon.style.display = 'none';
        if (iconSun) iconSun.style.display = 'block';
        if (themeText) themeText.innerText = 'Light Mode';
    }

    // Toggle listener
    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            updateThemeUI(isDark ? 'light' : 'dark');
        });
    }
});
