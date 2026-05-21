 // Navbar scroll effect
    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('.navbar').addClass('scrolled');
        } else {
            $('.navbar').removeClass('scrolled');
        }
        
        // Back to top button
        if ($(this).scrollTop() > 300) {
            $('.back-to-top').fadeIn('slow');
        } else {
            $('.back-to-top').fadeOut('slow');
        }
    });

    // Smooth scrolling for anchor links - FIXED VERSION
    $('a[href*="#"]').not('[href="#"]').not('[href="#0"]').on('click', function(e) {
        // Only prevent default if it's an anchor link on the same page
        if (this.pathname === window.location.pathname || this.hostname === window.location.hostname) {
            e.preventDefault();
            
            var target = $(this.hash);
            target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
            
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 70
                }, 500, 'linear');
                return false;
            }
        }
    });

    // Back to top button
    $('.back-to-top').click(function(e) {
        e.preventDefault();
        $('html, body').animate({scrollTop: 0}, 500);
        return false;
    });

    // Animation on scroll - FIXED VERSION
    $(document).ready(function() {
        // Check if Waypoint is available
        if ($.fn.waypoint) {
            $('.animate__animated').each(function() {
                var $this = $(this);
                var animation = '';
                
                // Extract animation class
                var classList = $this.attr('class').split(' ');
                for (var i = 0; i < classList.length; i++) {
                    if (classList[i].startsWith('animate__') && classList[i] !== 'animate__animated' && classList[i] !== 'animate__infinite') {
                        animation = classList[i];
                        break;
                    }
                }
                
                if (animation) {
                    $this.waypoint(function() {
                        $this.addClass(animation);
                    }, {
                        offset: '80%'
                    });
                }
            });
        }
    });

    // Fix for external links - make sure they work properly
    $(document).ready(function() {
        // Ensure all external links work normally
        $('a[href^="http"]').on('click', function(e) {
            // Don't prevent default - let the browser navigate
            return true;
        });
        
        // Fix for nav links with href
        $('.nav-link').on('click', function() {
            $('.nav-link').removeClass('active');
            $(this).addClass('active');
        });
    });

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });