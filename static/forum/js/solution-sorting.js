// static/forum/js/modules/solution-sorting.js

export class SolutionSorter {
    constructor() {
        this.currentSort = 'votes';
        this.initializeSortDropdown();
    }

    initializeSortDropdown() {
        const sortDropdown = document.getElementById('sortDropdown');
        const sortDropdownMenu = document.getElementById('sortDropdownMenu');
        const sortOptions = document.querySelectorAll('.sort-option');
        const currentSortText = document.getElementById('currentSort');

        if (!sortOptions.length || !currentSortText) {
            console.error("Sort elements not found in the DOM");
            return;
        }

        sortDropdown?.addEventListener('click', () => {
            sortDropdownMenu.classList.toggle('show');
        });

        sortOptions.forEach(option => {
            option.addEventListener("click", (e) => {
                e.preventDefault();
                const innerSortOptions = document.querySelectorAll('.sort-option');
                innerSortOptions.forEach(opt => opt.classList.remove('active'));
                
                this.currentSort = option.getAttribute("data-sort");
                currentSortText.textContent = this.currentSort.charAt(0).toUpperCase() + this.currentSort.slice(1);
                
                this.sortSolutions(this.currentSort);
                option.classList.add('active');
                sortDropdownMenu.classList.remove('show');
            });
        });

        this.sortSolutions(this.currentSort);
    }

    sortSolutions(sortBy) {
        const solutionsContainer = document.getElementById("solutions-container");
        if (!solutionsContainer) {
            console.error("Solutions container not found");
            return;
        }

        const acceptedSolution = document.querySelector(".accepted-solution");
        const regularSolutions = Array.from(
            document.querySelectorAll(".solution-container:not(.accepted-solution)")
        );

        if (sortBy === "votes") {
            regularSolutions.sort((a, b) => {
                const votesA = parseInt(a.querySelector(".vote-count").textContent) || 0;
                const votesB = parseInt(b.querySelector(".vote-count").textContent) || 0;
                return votesB - votesA;
            });
        } else if (sortBy === "recency") {
            regularSolutions.sort((a, b) => {
                const dateStrA = a.querySelector(".author-info .text-muted").textContent.replace("Answered ", "");
                const dateStrB = b.querySelector(".author-info .text-muted").textContent.replace("Answered ", "");
                const dateA = new Date(dateStrA);
                const dateB = new Date(dateStrB);
                return dateB - dateA;
            });
        }

        // Clear and rebuild the container
        while (solutionsContainer.firstChild) {
            solutionsContainer.removeChild(solutionsContainer.firstChild);
        }

        // Always add accepted solution first if it exists
        if (acceptedSolution) {
            solutionsContainer.appendChild(acceptedSolution);
        }

        // Add sorted regular solutions
        regularSolutions.forEach(solution => {
            solutionsContainer.appendChild(solution);
        });
    }
}