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
        button.addEventListener("click", function () {
            const itemId = button.dataset.itemId;
            alert("Edit functionality for item " + itemId + " is not implemented yet.");
        });
    });

    // 🔥 HAMBURGER MENU
const hamburger = document.querySelector(".hamburger");
const navbar = document.querySelector(".navbar");
const navLinks = document.querySelectorAll(".nav-links a");

// RESET STATE ON LOAD
if (navbar) navbar.classList.remove("open");
if (hamburger) hamburger.classList.remove("open");
navLinks.forEach(l => l.classList.remove("active"));

// TOGGLE MENU
if (hamburger && navbar) {
    hamburger.addEventListener("click", function () {
        navbar.classList.toggle("open");
        hamburger.classList.toggle("open");
    });
}

// NAV LINK CLICK LOGIC
navLinks.forEach(link => {
    link.addEventListener("click", function () {
        const href = this.getAttribute("href");

        // remove underline instantly (no animation flash)
        navLinks.forEach(l => {
            l.classList.add("no-anim");
            l.classList.remove("active");
        });

        // force reflow so transition reset applies immediately
        void document.body.offsetWidth;

        navLinks.forEach(l => l.classList.remove("no-anim"));

        // CLOSE MOBILE MENU
        if (navbar.classList.contains("open")) {
            navbar.classList.remove("open");
            hamburger.classList.remove("open");
        }

        // only keep active for real pages (optional — you can remove this entirely)
        if (!href.startsWith("#")) {
        }
    });
});

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

});