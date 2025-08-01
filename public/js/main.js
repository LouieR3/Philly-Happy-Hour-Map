$(function() {
	var siteSticky = function() {
	  $(".js-sticky-header").sticky({ topSpacing: 0 });
	};
	siteSticky();
	var siteMenuClone = function() {
	  $('.js-clone-nav').each(function() {
		var $this = $(this);
		$this.clone().attr('class', 'site-nav-wrap').appendTo('.site-mobile-menu-body');
	  });
	  setTimeout(function() {
		var counter = 0;
		$('.site-mobile-menu .has-children').each(function() {
		  var $this = $(this);
		  $this.prepend('<span class="arrow-collapse collapsed">');
		  $this.find('.arrow-collapse').attr({
			'data-toggle': 'collapse',
			'data-target': '#collapseItem' + counter,
		  });
		  $this.find('> ul').attr({
			'class': 'collapse',
			'id': 'collapseItem' + counter,
		  });
		  counter++;
		});
	  }, 1000);
  
	  $('body').on('click', '.arrow-collapse', function(e) {
		var $this = $(this);
		if ($this.closest('li').find('.collapse').hasClass('show')) {
		  $this.removeClass('active');
		} else {
		  $this.addClass('active');
		}
		e.preventDefault();
	  });
  
	  $(window).resize(function() {
		var $this = $(this),
		  w = $this.width();
  
		// Change the condition to 1100 pixels
		if (w > 1200) {
		  if ($('body').hasClass('offcanvas-menu')) {
			$('body').removeClass('offcanvas-menu');
		  }
		}
	  });
  
	  $('body').on('click', '.js-menu-toggle', function(e) {
		var $this = $(this);
		e.preventDefault();
  
		if ($('body').hasClass('offcanvas-menu')) {
		  $('body').removeClass('offcanvas-menu');
		  $this.removeClass('active');
		} else {
		  $('body').addClass('offcanvas-menu');
		  $this.addClass('active');
		}
	  });
  
	  // click outside offcanvas
	  $(document).mouseup(function(e) {
		var container = $(".site-mobile-menu");
		if (!container.is(e.target) && container.has(e.target).length === 0) {
		  if ($('body').hasClass('offcanvas-menu')) {
			$('body').removeClass('offcanvas-menu');
		  }
		}
	  });
	};
	siteMenuClone();
  });

  document.addEventListener('DOMContentLoaded', function () {
	var sections = document.querySelectorAll('.section'); // Adjust the selector based on your HTML structure
  
	function setActiveLink() {
	  var scrollPosition = window.scrollY || window.pageYOffset;
	  sections.forEach(function (section) {
		var sectionTop = section.offsetTop - 50; // Adjust the offset as needed
  
		if (scrollPosition >= sectionTop) {
		  var sectionId = section.getAttribute('id');
		  var correspondingLink = document.querySelector('a[href="#' + sectionId + '"]');
		  if (correspondingLink) {
			document.querySelectorAll('.nav-link').forEach(function (link) {
			  link.classList.remove('active');
			});
			correspondingLink.classList.add('active');
		  }
		}
	  });
	}
	setActiveLink(); // Set initial active link
	window.addEventListener('scroll', setActiveLink);
  });

//   // MAP BOX CODE
//   mapboxgl.accessToken = 'pk.eyJ1IjoibG91aWUzciIsImEiOiJjbGw0M3c5YXgwMjg5M2Nzc2twOXJ3M2tjIn0.vaR-SfpFZC26Go85Rv2leg';
//   const map = new mapboxgl.Map({
// 	  container: 'map', // container ID
// 	  style: 'mapbox://styles/louie3r/cm8htqvrv00v901s5f6py6yfo?optimize=true', // Map style
// 	  center: [-75.1652, 39.9526], // Center City, Philadelphia
// 	  zoom: 14,
// 	  minzoom: 15, // Adjust zoom to show more of Center City
// 	  maxzoom: 19 // Adjust zoom to show more of Center City
//   });

//   map.on('click', (event) => {
// 	// If the user clicked on one of your markers, get its information.
// 	const features = map.queryRenderedFeatures(event.point, {
// 	  layers: ['center-city-sips-bars'] // replace with your layer name
// 	});
// 	if (!features.length) {
// 	  return;
// 	}
// 	const feature = features[0];
// 	console.log(feature);
// 	console.log(feature.properties);

	
// 	const popup = new mapboxgl.Popup({ offset: [0, -15] })
// 	  .setLngLat(feature.geometry.coordinates)
// 	  .setHTML(
// 		`
// 		<h5 style="text-align: center;">${feature.properties.Name}</h5>
// 		<p style="text-align: center;">${feature.properties.Address}</p>
// 		<a  style="text-align: center; display: block;" href="${feature.properties.Website}" target="_blank" class="link">View their Website</a>
// 		<p style="text-align: center;"><b>Sips Deals:</b><br><b>$7 Cocktails:</b><br>${feature.properties.SIPS_COCKTAILS}<br><b>$6 Wine:</b><br>${feature.properties.SIPS_WINE}<br><b>$5 Beer:</b><br>${feature.properties.SIPS_BEER}<br><b>Half Priced Apps:</b><br>${feature.properties.SIPS_HALFPRICEDAPPS}</p>
// 		`
// 		// `<h5 style="text-align: center;">${feature.properties.Name}</h5>SIPS_COCKTAILS,SIPS_WINE,SIPS_BEER,SIPS_HALFPRICEDAPPS
// 		// <p style="text-align: center;">${feature.properties.Address}</p>
// 		// <a  style="text-align: center; display: block;" href="${feature.properties.Website}" target="_blank" class="link">View their Website</a>
// 		// <img src="${feature.properties.RW_PHOTO}" style="width: 80%; display: block; margin: auto; padding-top: 1rem;" alt="Photo of restaurant front">
// 		// `
// 	  )
// 	  .addTo(map);
//   });
//   /*
// 	Create a popup, specify its options
// 	and properties, and add it to the map.
//   */