(function () {
	function printElementById(id) {
		var el = document.getElementById(id);
		if (!el) {
			window.print();
			return;
		}

		var w = window.open('', '_blank', 'noopener,noreferrer');
		if (!w) {
			window.print();
			return;
		}

		w.document.open();
		w.document.write(
			'<!doctype html><html><head><meta charset="utf-8">' +
				'<meta name="viewport" content="width=device-width,initial-scale=1">' +
				'<title>Print</title>' +
				'</head><body>' +
				el.innerHTML +
				'</body></html>'
		);
		w.document.close();
		w.focus();
		w.print();
		w.close();
	}

	// Used by template-results.php
	window.printResult = function () {
		printElementById('resTable');
	};

	// Used by template-single-study.php
	window.printReceipt = function () {
		printElementById('single_study_data');
	};
})();
