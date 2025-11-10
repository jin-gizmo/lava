#!/bin/bash

# Generate markdown doco for the lava DynamoDB item templates that is suitable
# for use in the lava user guide.

CATEGORIES="job connection rule s3trigger"

TEMPLATE_DIR=templates
SECTION_HEADER='##'
# ITEM_HEADER='####'
ITEM_HEADER='???'

# ------------------------------------------------------------------------------
function initcap {
	python3 -c "print('$1'.capitalize())"
}

# ------------------------------------------------------------------------------
TMPDIR=$(mktemp -d)
z=3
trap '/bin/rm -rf $TMPDIR; exit $z' 0

# ------------------------------------------------------------------------------
for category in $CATEGORIES
do
	Category=$(initcap "$category")

	echo "*   [$Category samples](#$category-samples)" >> "$TMPDIR/idx"
	echo "$SECTION_HEADER $Category Samples" >> "$TMPDIR/body"

	for template in "$TEMPLATE_DIR"/"$category"/[a-z]*.yaml
	do
		item=$(expr "$(basename "$template")" : '\(.*\).yaml')

		echo "${ITEM_HEADER} \"$item\""
		echo
		echo '    ```yaml'
		./lava-item.py -p "${category}_id=demo" -P '???' "$category" "$item" | sed 's/^/    /'
		echo '    ```'
		echo
	done >> "$TMPDIR/body"
done

echo >> "$TMPDIR/idx"

cat "$TMPDIR/idx" "$TMPDIR/body"
z=0
