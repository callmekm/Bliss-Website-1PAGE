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
            if (!categoryId || !confirm("Delete this category and all its items?")) {
                return;
            }

            const response = await fetch(`/api/categories/${categoryId}`, {
                method: "DELETE",
                headers: { "Accept": "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert("Unable to delete category. Please try again.");
            }
        });
    });

    const deleteItemButtons = document.querySelectorAll(".delete-item");
    deleteItemButtons.forEach(function (button) {
        button.addEventListener("click", async function () {
            const itemId = button.dataset.itemId;
            if (!itemId || !confirm("Delete this item?")) {
                return;
            }

            const response = await fetch(`/api/items/${itemId}`, {
                method: "DELETE",
                headers: { "Accept": "application/json" },
            });

            if (response.ok) {
                window.location.reload();
            } else {
                alert("Unable to delete item. Please try again.");
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
            alert("Could not load item.");
            return;
        }

        const item = await response.json();

        const nameEn = prompt("English name:", item.name_en);
        if (nameEn === null) return;

        const nameMk = prompt("Macedonian name:", item.name_mk);
        if (nameMk === null) return;

        const descriptionEn = prompt("English description:", item.description_en || "");
        if (descriptionEn === null) return;

        const descriptionMk = prompt("Macedonian description:", item.description_mk || "");
        if (descriptionMk === null) return;

        const price = prompt("Price:", item.price || "");
        if (price === null) return;

        const featured = confirm("Should this item be featured? Press OK for yes, Cancel for no.");

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
            alert("Could not update item.");
        }
    });
});

// DELETE FEATURED ITEM
document.querySelectorAll(".delete-featured-item").forEach(button => {
    button.addEventListener("click", async () => {
        const id = button.dataset.featuredId;

        if (!id || !confirm("Delete this featured item?")) {
            return;
        }

        const response = await fetch(`/api/featured-items/${id}`, {
            method: "DELETE",
            headers: { "Accept": "application/json" },
        });

        if (response.ok) {
            window.location.reload();
        } else {
            alert("Unable to delete featured item.");
        }
    });
});

    //  HAMBURGER MENU
    const hamburger = document.querySelector(".hamburger");
    const navbar = document.querySelector(".navbar");
    const navLinks = document.querySelectorAll(".nav-links a:not(.lang-btn)");

    function syncNavLinkActiveFromHash() {
        const hash = window.location.hash || "";
        navLinks.forEach((l) => {
            const h = l.getAttribute("href") || "";
            l.classList.toggle("nav-link-active", hash !== "" && h === hash);
        });
    }

    // RESET STATE ON LOAD
    if (navbar) navbar.classList.remove("open");
    if (hamburger) hamburger.classList.remove("open");

    // TOGGLE MENU — opening clears section underline so it does not “stick” when reopening
    if (hamburger && navbar) {
        hamburger.addEventListener("click", function () {
            const opening = !navbar.classList.contains("open");
            navbar.classList.toggle("open");
            hamburger.classList.toggle("open");
            if (opening) {
                navLinks.forEach((l) => l.classList.remove("nav-link-active"));
            }
        });
    }

    // NAV LINK CLICK: close drawer + mark current section (hash links only)
    navLinks.forEach((link) => {
        link.addEventListener("click", function () {
            const href = this.getAttribute("href") || "";

            if (href.startsWith("#")) {
                navLinks.forEach((l) => l.classList.remove("nav-link-active"));
                this.classList.add("nav-link-active");
            } else {
                navLinks.forEach((l) => l.classList.remove("nav-link-active"));
            }

            if (navbar && navbar.classList.contains("open")) {
                navbar.classList.remove("open");
                hamburger.classList.remove("open");
            }
        });
    });

    window.addEventListener("hashchange", syncNavLinkActiveFromHash);
    syncNavLinkActiveFromHash();

    // DELETE SUBCATEGORY
    document.querySelectorAll(".delete-subcategory").forEach(button => {
        button.addEventListener("click", async () => {
            const id = button.dataset.subcategoryId;

            if (!confirm("Delete this subcategory?")) return;

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

    /* Visit Us → fit footer main block (logo → Instagram) in the viewport when possible */
    function scrollVisitUsFooterIntoView() {
        const footer = document.querySelector(".site-footer");
        const topEl = footer && footer.querySelector(".footer-intro");
        const bottomEl = footer && footer.querySelector(".footer-social");
        if (!topEl || !bottomEl) return;

        const scrollPadding =
            parseFloat(getComputedStyle(document.documentElement).scrollPaddingTop) || 90;
        const bottomGap = 16;

        const topY = topEl.getBoundingClientRect().top + window.scrollY;
        const bottomY = bottomEl.getBoundingClientRect().bottom + window.scrollY;
        const blockHeight = bottomY - topY;

        const available = window.innerHeight - scrollPadding - bottomGap;

        let scrollY;
        if (blockHeight <= available) {
            scrollY = topY - scrollPadding - (available - blockHeight) / 2;
        } else {
            scrollY = topY - scrollPadding;
        }

        const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
        /* ~1mm extra downward nudge (typical CSS px) */
        const scrollNudgePx = 4;
        scrollY = Math.max(0, Math.min(scrollY + scrollNudgePx, maxScroll));

        window.scrollTo({
            top: scrollY,
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

// FEATURED AUTO SLIDER
const featuredSlides = document.querySelectorAll(".featured-slide");
const featuredDots = document.querySelectorAll(".featured-dot");
let currentFeaturedSlide = 0;

function showFeaturedSlide(index) {
    if (!featuredSlides.length) return;

    featuredSlides.forEach(slide => slide.classList.remove("active"));
    featuredDots.forEach(dot => dot.classList.remove("active"));

    featuredSlides[index].classList.add("active");

    if (featuredDots[index]) {
        featuredDots[index].classList.add("active");
    }

    currentFeaturedSlide = index;
}

if (featuredSlides.length) {
    setInterval(() => {
        const nextSlide = (currentFeaturedSlide + 1) % featuredSlides.length;
        showFeaturedSlide(nextSlide);
    }, 5000);
}

featuredDots.forEach(dot => {
    dot.addEventListener("click", function () {
        const index = Number(this.dataset.slide);
        showFeaturedSlide(index);
    });
});