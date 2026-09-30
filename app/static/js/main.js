// Submit the form when the user checks "Complete" on the actions page.
document.querySelectorAll(".complete-checkbox").forEach((checkbox) => {
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      checkbox.closest("form").requestSubmit();
    }
  });
});
