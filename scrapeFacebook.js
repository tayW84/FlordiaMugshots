(function() {
    window.capturedUrls = window.capturedUrls || new Set();
    
    const collectImages = () => {
        const currentImages = document.querySelectorAll('img[src*="scontent"]');
        let addedInThisCheck = 0;
        
        currentImages.forEach(img => {
            if (!window.capturedUrls.has(img.src)) {
                window.capturedUrls.add(img.src);
                addedInThisCheck++;
            }
        });
        
        if (addedInThisCheck > 0) {
            console.log(`Total unique images collected: ${window.capturedUrls.size}`);
        }
    };

    // Run the collector every 2 seconds
    const scrollInterval = setInterval(collectImages, 2000);
    
    console.log("Collector started! Scroll down slowly. Type 'stopCollect()' to stop and see the final list.");
    
    window.stopCollect = () => {
        clearInterval(scrollInterval);
        console.log(`Final Count: ${window.capturedUrls.size}`);
        console.log("The list of URLs is stored in 'window.capturedUrls'");
        // Optional: Copy the list to your clipboard
        copy(Array.from(window.capturedUrls).join('\n'));
        console.log("URLs have been copied to your clipboard!");
    };
})();
//Copy and paste this into console in chrome, then scroll until we collect enough pictures.
// run stopCollecter() to save image links to clipboard.