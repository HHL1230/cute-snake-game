document.addEventListener('DOMContentLoaded', () => {

    // Navbar 滾動效果
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // 行動版選單切換
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');

    menuToggle.addEventListener('click', () => {
        navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
        if (navLinks.style.display === 'flex') {
            navLinks.style.flexDirection = 'column';
            navLinks.style.position = 'absolute';
            navLinks.style.top = '70px';
            navLinks.style.right = '0';
            navLinks.style.background = '#0d0d0d';
            navLinks.style.width = '100%';
            navLinks.style.padding = '2rem';
            navLinks.style.textAlign = 'center';
            navLinks.style.borderBottom = '1px solid #333';
        }
    });

    // 使用 Intersection Observer 實現滾動顯現動畫
    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const revealElements = document.querySelectorAll('.about-text, .about-image, .menu-item, .visit-info, .banner-content');

    revealElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.8s ease-out, transform 0.8s ease-out';
        observer.observe(el);
    });

    // 動態添加 visible 樣式
    const style = document.createElement('style');
    style.innerHTML = `
        .visible {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(style);

    // 橫幅視差效果
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const banner = document.querySelector('.banner');
        if (banner) {
            // 通過稍微調整背景位置實現簡單視差
            // 注意：background-attachment: fixed 已經完成了大部分工作，
            // 但這可以為內容增加額外的深度
            const limit = banner.offsetTop + banner.offsetHeight;
            if (scrolled > banner.offsetTop - window.innerHeight && scrolled < limit) {
                const speed = 0.5;
                const yPos = -(scrolled * speed / 5);
                // banner.style.backgroundPosition = `center ${yPos}px`; 
                // 因與 css fixed 衝突而禁用
            }
        }
    });
});
