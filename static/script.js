document.addEventListener("DOMContentLoaded", function () {
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

    // 🔥 HAMBURGER MENU (your existing logic)
    const hamburger = document.querySelector(".hamburger");
    const navbar = document.querySelector(".navbar");

    if (hamburger && navbar) {
        hamburger.addEventListener("click", function () {
            navbar.classList.toggle("open");
        });
    }

    // ✅ NEW: ACTIVE NAV LINK
    const navLinks = document.querySelectorAll(".nav-links a");

    navLinks.forEach(link => {
        link.addEventListener("click", function () {
            navLinks.forEach(l => l.classList.remove("active"));
            this.classList.add("active");
        });
    });

});