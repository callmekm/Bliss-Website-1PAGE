document.addEventListener("DOMContentLoaded", function () {
    /* ----- Public site: mobile nav ----- */
    const siteNavbar = document.querySelector(".site-navbar");
    const siteBurger = document.querySelector(".site-hamburger");
    const siteNavLinks = document.querySelectorAll(".site-nav-menu .site-nav-link");

    if (siteBurger && siteNavbar) {
        siteBurger.addEventListener("click", function () {
            const open = siteNavbar.classList.toggle("is-open");
            siteBurger.setAttribute("aria-expanded", open ? "true" : "false");
        });

        siteNavLinks.forEach(function (link) {
            link.addEventListener("click", function () {
                siteNavbar.classList.remove("is-open");
                siteBurger.setAttribute("aria-expanded", "false");
            });
        });
    }

    /* ----- Public site: menu accordions ----- */
    document.querySelectorAll(".menu-category > .menu-category-header").forEach(function (button) {
        button.addEventListener("click", function () {
            const category = button.closest(".menu-category");
            if (!category) {
                return;
            }
            const isOpen = category.classList.toggle("open");
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    });

    document.querySelectorAll(".subcategory-header").forEach(function (button) {
        button.addEventListener("click", function () {
            const block = button.closest(".menu-subcategory");
            if (!block) {
                return;
            }
            const isOpen = block.classList.toggle("open");
            button.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });
    });

    /* ----- Admin: delete category ----- */
    document.querySelectorAll(".delete-category").forEach(function (button) {
        button.addEventListener("click", async function () {
            const categoryId = button.dataset.categoryId;
            if (!categoryId || !confirm("Delete this category and all its items?")) {
                return;
            }

            const response = await fetch("/api/categories/" + categoryId, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert("Unable to delete category. Please try again.");
            }
        });
    });

    /* ----- Admin: delete item ----- */
    document.querySelectorAll(".delete-item").forEach(function (button) {
        button.addEventListener("click", async function () {
            const itemId = button.dataset.itemId;
            if (!itemId || !confirm("Delete this item?")) {
                return;
            }

            const response = await fetch("/api/items/" + itemId, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert("Unable to delete item. Please try again.");
            }
        });
    });

    document.querySelectorAll(".edit-item").forEach(function (button) {
        button.addEventListener("click", function () {
            const itemId = button.dataset.itemId;
            alert("Edit functionality for item " + itemId + " is not implemented yet.");
        });
    });

    /* ----- Public site: featured carousel (scoped) ----- */
    (function initFeaturedCarousel() {
        var root = document.querySelector(".featured-carousel");
        if (!root) {
            return;
        }

        var viewport = root.querySelector(".featured-carousel-viewport");
        var track = root.querySelector(".featured-carousel-track");
        var slides = root.querySelectorAll(".featured-slide");
        var prevBtn = root.querySelector(".featured-carousel-btn--prev");
        var nextBtn = root.querySelector(".featured-carousel-btn--next");

        var total = slides.length;
        if (!viewport || !track || total === 0) {
            return;
        }

        var index = 0;
        var reduceMotion =
            window.matchMedia &&
            window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (reduceMotion) {
            root.classList.add("is-reduced-motion");
        }

        var autoplayMs = 5500;
        var rawMs = root.getAttribute("data-autoplay-ms");
        if (rawMs) {
            var parsedMs = parseInt(rawMs, 10);
            if (!isNaN(parsedMs) && parsedMs > 0) {
                autoplayMs = parsedMs;
            }
        }

        var autoplayId = null;
        var hoverInside = false;

        function stopAutoplay() {
            if (autoplayId !== null) {
                clearInterval(autoplayId);
                autoplayId = null;
            }
        }

        function focusInsideRoot() {
            var el = document.activeElement;
            return !!(el && root.contains(el));
        }

        function startAutoplay() {
            stopAutoplay();
            if (
                reduceMotion ||
                total <= 1 ||
                document.hidden ||
                hoverInside ||
                focusInsideRoot()
            ) {
                return;
            }
            autoplayId = setInterval(function () {
                go(1, true);
            }, autoplayMs);
        }

        function resetAutoplayTimer() {
            stopAutoplay();
            startAutoplay();
        }

        function go(delta, fromAutoplay) {
            if (total <= 1) {
                return;
            }
            index = (index + delta + total) % total;
            applyTransform();
            if (!fromAutoplay) {
                resetAutoplayTimer();
            }
        }

        function applyTransform() {
            track.style.transform = "translate3d(" + -index * 100 + "%, 0, 0)";
        }

        applyTransform();

        if (total > 1) {
            document.addEventListener("visibilitychange", function () {
                if (document.hidden) {
                    stopAutoplay();
                } else {
                    startAutoplay();
                }
            });

            root.addEventListener("mouseenter", function () {
                hoverInside = true;
                stopAutoplay();
            });
            root.addEventListener("mouseleave", function () {
                hoverInside = false;
                startAutoplay();
            });
            root.addEventListener("focusin", function () {
                stopAutoplay();
            });
            root.addEventListener("focusout", function (e) {
                if (root.contains(e.relatedTarget)) {
                    return;
                }
                setTimeout(function () {
                    startAutoplay();
                }, 0);
            });

            startAutoplay();
        }

        if (prevBtn) {
            prevBtn.addEventListener("click", function () {
                go(-1);
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener("click", function () {
                go(1);
            });
        }

        viewport.addEventListener("keydown", function (e) {
            if (e.key === "ArrowLeft") {
                e.preventDefault();
                go(-1);
            } else if (e.key === "ArrowRight") {
                e.preventDefault();
                go(1);
            }
        });

        var touchStartX = null;
        viewport.addEventListener(
            "touchstart",
            function (e) {
                touchStartX = e.changedTouches[0].screenX;
            },
            { passive: true }
        );
        viewport.addEventListener(
            "touchend",
            function (e) {
                if (touchStartX === null || total <= 1) {
                    return;
                }
                var dx = e.changedTouches[0].screenX - touchStartX;
                var threshold = 48;
                if (dx < -threshold) {
                    go(1);
                } else if (dx > threshold) {
                    go(-1);
                }
                touchStartX = null;
            },
            { passive: true }
        );
    })();

    /* ----- Admin: delete subcategory ----- */
    document.querySelectorAll(".delete-subcategory").forEach(function (button) {
        button.addEventListener("click", async function () {
            const id = button.dataset.subcategoryId;
            if (!id || !confirm("Delete this subcategory?")) {
                return;
            }

            const res = await fetch("/api/subcategories/" + id, {
                method: "DELETE",
            });

            if (res.ok) {
                location.reload();
            }
        });
    });
});
