document.addEventListener('DOMContentLoaded', function() {
    console.log("JavaScript is running");
    const slides = document.querySelectorAll('.carousel-slide');
    const prevButton = document.querySelector('.prev');
    const nextButton = document.querySelector('.next');
    let currentSlide = 0;

    function showSlide(n) {
        slides[currentSlide].classList.remove('active');
        currentSlide = (n + slides.length) % slides.length;
        slides[currentSlide].classList.add('active');
    }

    function toggleNavigationButtons() {
        if (slides.length <= 1) {
            prevButton.style.display = "none";
            nextButton.style.display = "none";
        } else {
            prevButton.style.display = "block";
            nextButton.style.display = "block";
        }
    }



    prevButton.addEventListener('click', () => showSlide(currentSlide - 1));
    nextButton.addEventListener('click', () => showSlide(currentSlide + 1));

    toggleNavigationButtons();

    //Video.js
    videojs.log.level('debug');
    console.log("Approaching video section");

    const videoElements = document.querySelectorAll('.video-js');

    if (videoElements.length === 0) {
        console.error("No video elements found!");
        return;
    }

    videoElements.forEach(video => {
        if (!video.id) {
            console.error("Video element without an ID:", video);
            return;
        }

        try {
            const player = videojs(video.id, {
                controlBar: {
                    volumePanel: { inline: false },
                    playbackRateMenuButton: true
                },
                playbackRates: [0.5, 1, 1.5, 2],
            });

            player.on('ready', () => {
                console.log(`Player for ${video.id} is ready.`);
            });

            player.on('ended', () => {
                console.log(`Video ${video.id} has ended.`);
            });
        } catch (error) {
            console.error(`Error initializing video.js for ${video.id}:`, error);
        }
    });
});