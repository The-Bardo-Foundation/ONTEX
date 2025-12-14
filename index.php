<?php
/**
 * WordPress theme fallback template.
 *
 * This file is required for WordPress themes.
 */

define('ONTEX_THEME_LOADED', true);

get_header();
?>
<main class="container">
	<h1><?php echo esc_html(get_bloginfo('name')); ?></h1>
	<p><?php echo esc_html(get_bloginfo('description')); ?></p>
</main>
<?php
get_footer();
