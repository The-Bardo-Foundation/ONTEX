<?php

/**
 * Helper functions used by the ONTEX templates.
 */

if (!defined('ABSPATH')) {
	exit;
}

if (!function_exists('ontex_normalize_value')) {
	/**
	 * Normalize API/object values to a printable string.
	 *
	 * @param mixed $value
	 */
	function ontex_normalize_value($value): string
	{
		if ($value === null) {
			return '';
		}

		if (is_bool($value)) {
			return $value ? '1' : '0';
		}

		if (is_scalar($value)) {
			return (string) $value;
		}

		if (is_array($value)) {
			$flat = [];
			foreach ($value as $v) {
				$v = ontex_normalize_value($v);
				if ($v !== '') {
					$flat[] = $v;
				}
			}
			$flat = array_values(array_unique($flat));
			return implode(', ', $flat);
		}

		// Objects: try common string cast patterns.
		if (is_object($value) && method_exists($value, '__toString')) {
			return (string) $value;
		}

		return '';
	}
}

if (!function_exists('getCustomData')) {
	/**
	 * Echo a field value from an object, preferring a custom override field.
	 *
	 * The existing templates call this directly.
	 *
	 * @param string $key        Base key (e.g. 'Phase')
	 * @param string $customKey  Custom override key (e.g. 'CustomPhase')
	 * @param object $obj        Data object
	 */
	function getCustomData(string $key, string $customKey, $obj): void
	{
		$raw = '';

		if (is_object($obj)) {
			if (property_exists($obj, $customKey) && ontex_normalize_value($obj->{$customKey}) !== '') {
				$raw = ontex_normalize_value($obj->{$customKey});
			} elseif (property_exists($obj, $key)) {
				$raw = ontex_normalize_value($obj->{$key});
			}
		}

		$raw = trim($raw);
		if ($raw === '') {
			echo '-';
			return;
		}

		// Allow limited markup when the source includes HTML.
		if (strpos($raw, '<') !== false) {
			echo wp_kses_post($raw);
			return;
		}

		echo esc_html($raw);
	}
}
