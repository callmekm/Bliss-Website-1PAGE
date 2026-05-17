function adminUi(key, fallback) {
    var pack = typeof window !== "undefined" ? window.__ADMIN_UI_I18N : null;
    if (pack && typeof pack[key] === "string") {
        return pack[key];
    }
    return fallback;
}

document.addEventListener("DOMContentLoaded", function () {
    const langBtn = document.querySelector(".nav-top .lang-btn");

    if (langBtn) {
        langBtn.addEventListener("click", function () {
            this.classList.add("active");
        });
    }

    const categoryButtons = document.querySelectorAll(".category-toggle");

    categoryButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const items = button.nextElementSibling;
            items.classList.toggle("open");
            button.classList.toggle("open"); // ADD THIS
        });
    });

    const deleteCategoryButtons = document.querySelectorAll(".delete-category");
    deleteCategoryButtons.forEach(function (button) {
        button.addEventListener("click", async function () {
            const categoryId = button.dataset.categoryId;
            if (!categoryId || !confirm(adminUi("confirmDeleteCategory", "Delete this category and all its items?"))) {
                return;
            }

            const response = await fetch(`/api/categories/${categoryId}`, {
                method: "DELETE",
                headers: { "Accept": "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert(adminUi("alertDeleteCategoryFailed", "Unable to delete category. Please try again."));
            }
        });
    });

    const deleteItemButtons = document.querySelectorAll(".delete-item");
    deleteItemButtons.forEach(function (button) {
        button.addEventListener("click", async function () {
            const itemId = button.dataset.itemId;
            if (!itemId || !confirm(adminUi("confirmDeleteItem", "Delete this item?"))) {
                return;
            }

            const response = await fetch(`/api/items/${itemId}`, {
                method: "DELETE",
                headers: { "Accept": "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert(adminUi("alertDeleteItemFailed", "Unable to delete item. Please try again."));
            }
        });
    });
const editItemButtons = document.querySelectorAll(".edit-item");

editItemButtons.forEach(function (button) {
    button.addEventListener("click", async function () {
        const itemId = button.dataset.itemId;

        const response = await fetch(`/api/items/${itemId}`, {
            method: "GET",
            headers: { "Accept": "application/json" },
        });

        if (!response.ok) {
            alert(adminUi("alertLoadItemFailed", "Could not load item."));
            return;
        }

        const item = await response.json();

        const nameEn = prompt(adminUi("promptEnglishName", "English name:"), item.name_en);
        if (nameEn === null) return;

        const nameMk = prompt(adminUi("promptMacedonianName", "Macedonian name:"), item.name_mk);
        if (nameMk === null) return;

        const descriptionEn = prompt(adminUi("promptEnglishDescription", "English description:"), item.description_en || "");
        if (descriptionEn === null) return;

        const descriptionMk = prompt(
            adminUi("promptMacedonianDescription", "Macedonian description:"),
            item.description_mk || ""
        );
        if (descriptionMk === null) return;

        const price = prompt(adminUi("promptPrice", "Price:"), item.price || "");
        if (price === null) return;

        const featured = confirm(
            adminUi(
                "confirmFeaturedItem",
                "Should this item be featured? Press OK for yes, Cancel for no."
            )
        );

        const updateResponse = await fetch(`/api/items/${itemId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body: JSON.stringify({
                name_en: nameEn,
                name_mk: nameMk,
                description_en: descriptionEn,
                description_mk: descriptionMk,
                price: price,
                featured: featured,
            }),
        });

        if (updateResponse.ok) {
            window.location.reload();
        } else {
            alert(adminUi("alertUpdateItemFailed", "Could not update item."));
        }
    });
});

// DELETE FEATURED ITEM
document.querySelectorAll(".delete-featured-item").forEach(button => {
    button.addEventListener("click", async () => {
        const id = button.dataset.featuredId;

        if (!id || !confirm(adminUi("confirmDeleteFeaturedItem", "Delete this featured item?"))) {
            return;
        }

        const response = await fetch(`/api/featured-items/${id}`, {
            method: "DELETE",
            headers: { "Accept": "application/json" },
        });

        if (response.ok) {
            window.location.reload();
        } else {
            alert(adminUi("alertDeleteFeaturedFailed", "Unable to delete featured item."));
        }
    });
});

    //  HAMBURGER MENU
    const hamburger = document.querySelector(".hamburger");
    const navbar = document.querySelector(".navbar");
    const navLinks = document.querySelectorAll(".nav-links a:not(.lang-btn)");

    function syncNavLinkActiveFromHash() {
        navLinks.forEach((l) => l.classList.remove("nav-link-active"));
    }

    // RESET STATE ON LOAD
    if (navbar) navbar.classList.remove("open");
    if (hamburger) hamburger.classList.remove("open");

    // TOGGLE MENU
    if (hamburger && navbar) {
        hamburger.addEventListener("click", function () {
            navbar.classList.toggle("open");
            hamburger.classList.toggle("open");
        });
    }

    // NAV LINK CLICK: close drawer; underline stays hover-only
    navLinks.forEach((link) => {
        link.addEventListener("click", function (e) {
            const href = this.getAttribute("href") || "";
            navLinks.forEach((l) => l.classList.remove("nav-link-active"));

            if (navbar && navbar.classList.contains("open")) {
                navbar.classList.remove("open");
                hamburger.classList.remove("open");
            }

            if (href === "#featured") {
                e.preventDefault();

                const featured = document.querySelector("#featured");
                if (!featured) return;

                const scrollPadding =
                    parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 90;
                const extraDown = 70;
                const targetTop = featured.getBoundingClientRect().top + window.scrollY - scrollPadding + extraDown;

                window.scrollTo({
                    top: Math.max(0, targetTop),
                    behavior: "smooth",
                });

                history.pushState(null, "", href);
            }
        });
    });

    window.addEventListener("hashchange", syncNavLinkActiveFromHash);
    syncNavLinkActiveFromHash();

    // DELETE SUBCATEGORY
    document.querySelectorAll(".delete-subcategory").forEach(button => {
        button.addEventListener("click", async () => {
            const id = button.dataset.subcategoryId;

            if (!confirm(adminUi("confirmDeleteSubcategory", "Delete this subcategory?"))) return;

            const res = await fetch(`/api/subcategories/${id}`, {
                method: "DELETE"
            });

            if (res.ok) location.reload();
        });
    });

    // SUBCATEGORY TOGGLE
    const subcategoryHeaders = document.querySelectorAll(".menu-subcategory h4");

    subcategoryHeaders.forEach(header => {
        header.addEventListener("click", function () {
            const parent = this.parentElement;
            parent.classList.toggle("open");
        });
    });

    /* Visit Us → scroll to the bottom of the page */
    function scrollVisitUsFooterIntoView() {
        const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);

        window.scrollTo({
            top: maxScroll,
            behavior: "smooth",
        });
    }

    document.querySelectorAll('a[href="#footer"]').forEach(function (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            scrollVisitUsFooterIntoView();
        });
    });

});

// FEATURED CAROUSEL — fade between slides, 5s autoplay, dot indicators
const featuredSlides = document.querySelectorAll(".featured-slide");
const featuredDots = document.querySelectorAll(".featured-dot");
const featuredSwipeArea = document.querySelector(".featured-slides");
let currentFeaturedSlide = 0;
let featuredAutoplayId = null;
let featuredSwipeStartX = 0;
let featuredSwipeStartY = 0;
let featuredSwipePointerId = null;

function showFeaturedSlide(index) {
    if (!featuredSlides.length) return;

    const n = featuredSlides.length;
    const i = ((index % n) + n) % n;

    featuredSlides.forEach(function (slide, idx) {
        const on = idx === i;
        slide.classList.toggle("active", on);
        slide.setAttribute("aria-hidden", on ? "false" : "true");
    });

    featuredDots.forEach(function (dot, idx) {
        const on = idx === i;
        dot.classList.toggle("active", on);
        dot.setAttribute("aria-selected", on ? "true" : "false");
    });

    currentFeaturedSlide = i;
}

function startFeaturedAutoplay() {
    if (featuredAutoplayId !== null) {
        clearInterval(featuredAutoplayId);
        featuredAutoplayId = null;
    }
    if (featuredSlides.length <= 1) return;

    featuredAutoplayId = window.setInterval(function () {
        showFeaturedSlide(currentFeaturedSlide + 1);
    }, 5000);
}

startFeaturedAutoplay();

featuredDots.forEach(function (dot) {
    dot.addEventListener("click", function () {
        const index = Number(dot.dataset.slide);
        if (Number.isNaN(index)) return;
        showFeaturedSlide(index);
        startFeaturedAutoplay();
    });
});

if (featuredSwipeArea && featuredSlides.length > 1) {
    featuredSwipeArea.addEventListener("pointerdown", function (e) {
        featuredSwipeStartX = e.clientX;
        featuredSwipeStartY = e.clientY;
        featuredSwipePointerId = e.pointerId;
        featuredSwipeArea.setPointerCapture(e.pointerId);
    });

    featuredSwipeArea.addEventListener("pointerup", function (e) {
        if (featuredSwipePointerId !== e.pointerId) return;

        const deltaX = e.clientX - featuredSwipeStartX;
        const deltaY = e.clientY - featuredSwipeStartY;
        const isHorizontalSwipe = Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY) * 1.3;

        featuredSwipePointerId = null;

        if (!isHorizontalSwipe) return;

        showFeaturedSlide(currentFeaturedSlide + (deltaX < 0 ? 1 : -1));
        startFeaturedAutoplay();
    });

    featuredSwipeArea.addEventListener("pointercancel", function () {
        featuredSwipePointerId = null;
    });
}