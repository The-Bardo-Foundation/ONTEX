<?php

// Prevent direct access.
if (!defined('ABSPATH')) {
	exit;
}

require_once __DIR__ . '/inc/helpers.php';

add_action('wp_enqueue_scripts', function () {
	// Small helper script used by the page templates for printing.
	wp_enqueue_script(
		'ontex-print',
		get_template_directory_uri() . '/assets/js/ontex-print.js',
		[],
		'0.1.0',
		true
	);
});
