class AnsiTerm {
    constructor(pid, width) {
        this.pid = pid;
        this.row = 0;
        this.col = 0;
        this.width = width;
        this.grid = [[new Array(width)]]; // addressed with grid[row][wrapping][col]
        this.moveCursor(this.row, this.col);
    }

    clear() {
        $('#programLog_' + this.pid).empty();
        this.row = 0;
        this.col = 0;
        this.rest = '';
        this.savedCursor = [0, 0];
        this.grid = [[new Array(this.width)]];
        this.moveCursor(this.row, this.col);
    }

    insertText(text, row, col) {
        let wrapping = Math.floor(col / this.width);
        this.grid[row][wrapping][col % this.width] = text;
    }

    insertTextAtCursor(text) {
        this.insertText(text, this.row, this.col);
    }

    updateHtml() {
        // TODO could be speed up on updates by only updating changed lines
        for (let row = 0; row < this.grid.length; row++) {
            let completedRow = [];

            // gather text of a whole row
            for (let wrap = 0; wrap < this.grid[row].length; wrap++) {
                let text = '';
                for (let col = 0; col < this.grid[row][wrap].length; col++) {
                    if (this.grid[row][wrap][col] != null) {
                        text += this.grid[row][wrap][col];
                    } else {
                        text += ' ';
                    }
                }
                completedRow.push(text);
            }

            // remove empty trailing line wraps
            for (let wrap = completedRow.length - 1; wrap > 0; wrap--) {
                if (completedRow[wrap].match(/^\s+$/)) {
                    completedRow.pop();
                    this.grid[row].pop();
                    $('#' + this.pid + '_term_' + row + '_' + wrap).remove();
                } else {
                    break;
                }
            }
            for (let wrap = 0; wrap < this.grid[row].length; wrap++) {
                $('#' + this.pid + '_term_' + row + '_' + wrap).text(completedRow[wrap] + '\n');
            }
        }
    }

    moveCursor(row, col) {
        for (let i = this.grid.length - 1; i <= row; i++) {
            let nextRow = $('<span/>', {
                class: 'term-row-' + i,
                id: this.pid + '_term_' + i + '_0',
                text: '',
            });
            nextRow.data('wrap-id', 0);
            $('#programLog_' + this.pid).append(nextRow);

            this.grid.push([new Array(this.width)]);
        }

        for (let i = this.grid[row].length; i <= Math.floor(col / this.width); i++) {
            let wrappingRow = $('<span/>', {
                class: 'term-row-' + row,
                id: this.pid + '_term_' + row + '_' + i,
                text: '',
            });
            wrappingRow.data('wrap-id', i);
            wrappingRow.insertAfter($('#' + this.pid + '_term_' + row + '_' + (i - 1)));

            this.grid[row].push(new Array(this.width));
        }

        this.row = row;
        this.col = col;
    }

    feed(text) {
        text = this.rest + text;
        this.rest = '';
        for (let i = 0; i < text.length; i++) {
            let c = text.charAt(i);
            switch (c) {
                // TODO missing escape codes && save uncomplete commands on the end of the text
                case '\u001B':
                    let rest = text.substring(i, i + 20);
                    let matches = null;

                    /** CUU/CUD/CUF/CUB/CNL/CPL/CHA  Cursor Movement
                     * Moves the cursor {\displaystyle n} n (default 1) cells in
                     * the given direction. If the cursor is already at the edge
                     * of the screen, this has no effect.
                     **/
                    if ((matches = rest.match(/^\u001B\[(\d*)[A-G]/))) {
                        i = i + matches[0].length - '\x1b'.length;
                        if (matches[1] == '') {
                            matches[1] = '1';
                        }

                        switch (matches[0].slice(-1)) {
                            // Up
                            case 'A':
                                if (this.row - parseInt(matches[1]) > 0) {
                                    this.moveCursor(this.row - parseInt(matches[1]), this.col);
                                }
                                break;
                            // Down
                            case 'B':
                                this.moveCursor(this.row + parseInt(matches[1]), this.col);
                                break;
                            // Forward
                            case 'C':
                                this.moveCursor(this.row, this.col + parseInt(matches[1]));
                                break;
                            // Backward
                            case 'D':
                                if (this.col - parseInt(matches[1]) > 0) {
                                    this.moveCursor(this.row, this.col - parseInt(matches[1]));
                                }
                                break;
                            // Beginning of next line
                            case 'E':
                                this.moveCursor(this.row + parseInt(matches[1]), 0);
                                break;
                            // Beginning of previous Line
                            case 'F':
                                if (this.row - parseInt(matches[1]) > 0) {
                                    this.moveCursor(this.row - parseInt(matches[1]), 0);
                                }
                                break;
                            // Horizontal Absolute
                            case 'G':
                                this.moveCursor(this.row, parseInt(matches[1]) - 1);
                                break;
                        }
                        break;
                    }

                    /** EL – Erase in Line
                     * Erases part of the line. If {\displaystyle n} n is zero
                     * (or missing), clear from cursor to the end of the line.
                     * If {\displaystyle n} n is one, clear from cursor to
                     * beginning of the line. If {\displaystyle n} n is two,
                     * clear entire line. Cursor position does not change.
                     **/
                    if ((matches = rest.match(/^\u001B\[(\d*)K/))) {
                        i = i + matches[0].length - '\x1b'.length;

                        let mode = matches[1];
                        if (mode === '') {
                            mode = 0;
                        }
                        switch (mode) {
                            case 0:
                                for (let i = this.col; i < this.width * this.grid[this.row].length; i++) {
                                    this.insertText(' ', this.row, i);
                                }
                                break;
                            case 1:
                                for (let i = 0; i <= this.col; i++) {
                                    this.insertText(' ', this.row, i);
                                }
                                break;
                            case 2:
                                for (let i = 0; i < this.width * this.grid[this.row].length; i++) {
                                    this.insertText(' ', this.row, i);
                                }
                                break;
                            default:
                                break;
                        }
                        break;
                    }

                    /** ED – Erase in Display
                     * Clears part of the screen. If {\displaystyle n} n is 0 (or missing), clear from cursor to end of
                     * screen. If {\displaystyle n} n is 1, clear from cursor to beginning of the screen. If
                     * {\displaystyle n} n is 2, clear entire screen (and moves cursor to upper left on DOS ANSI.SYS).
                     * If {\displaystyle n} n is 3, clear entire screen and delete all lines saved in the scrollback
                     * buffer (this feature was added for xterm and is supported by other terminal applications).
                     **/
                    if ((matches = rest.match(/^\u001B\[(\d*)J/))) {
                        i = i + matches[0].length - '\x1b'.length;

                        let mode = matches[1];
                        if (mode === '') {
                            mode = 0;
                        }

                        switch (mode) {
                            case 0:
                                for (let i = this.col; i < this.width * this.grid[this.row].length; i++) {
                                    this.insertText(' ', this.row, i);
                                }
                                for (let i = this.row; i < this.grid.length; i++) {
                                    for (let j = 0; j < this.width * this.grid[i].length; j++) {
                                        this.insertText(' ', i, j);
                                    }
                                }
                                break;
                            case 1:
                                for (let i = 0; i < this.row; i++) {
                                    for (let j = 0; j < this.width * this.grid[i].length; j++) {
                                        this.insertText(' ', i, j);
                                    }
                                }
                                for (let i = 0; i <= this.col; i++) {
                                    this.insertText(' ', this.row, i);
                                }
                                break;
                            case 2:
                            case 3:
                                for (let i = 0; i < this.grid.length; i++) {
                                    for (let j = 0; j < this.width * this.grid[i].length; j++) {
                                        this.insertText(' ', i, j);
                                    }
                                }
                                break;
                        }
                        break;
                    }

                    /** CUP – Cursor Position
                     * Moves the cursor to row {\displaystyle n} n, column
                     * {\displaystyle m} m. The values are 1-based, and default
                     * to 1 (top left corner) if omitted. A sequence such as
                     * CSI ;5H is a synonym for CSI 1;5H as well as CSI 17;H is
                     * the same as CSI 17H and CSI 17;1H
                     **/
                    if ((matches = rest.match(/^\u001B\[(((\d*);(\d*))?)[Hf]/))) {
                        i = i + matches[0].length - '\x1b'.length;

                        let row = parseInt(matches[3]) - 1;
                        if (isNaN(row)) {
                            row = 0;
                        }

                        let col = parseInt(matches[4]) - 1;
                        if (isNaN(col)) {
                            col = 0;
                        }

                        this.moveCursor(row, col);
                        break;
                    }

                    /** SCP – Save Cursor Position
                     * Saves the cursor position/state.
                     */
                    if ((matches = rest.match(/^\u001B\[s/))) {
                        i = i + matches[0].length - '\x1b'.length;
                        this.savedCursor = [this.row, this.col];
                        break;
                    }

                    /** RCP – Restore Cursor Position
                     * Restores the cursor position/state.
                     */
                    if ((matches = rest.match(/^\u001B\[u/))) {
                        i = i + matches[0].length - '\x1b'.length;
                        this.row = this.savedCursor[0];
                        this.col = this.savedCursor[1];
                        break;
                    }

                    // currently ignored Codes
                    if ((matches = rest.match(/^\u001B\[((\d*)(((;+)(\d*))*))m/)) ||
                        (matches = rest.match(/^\u001B\[\?((\d*)(((;+)(\d*))*))[hl]/)) || 
                        (matches = rest.match(/^\u001B\(B/)) ||
                        (matches = rest.match(/^\u001B\[((\d*)(((;+)(\d*))*))[trl]/)) ||
                        (matches = rest.match(/^\u001B\[(\d*)[Xd]/)) ||
                        (matches = rest.match(/^\u001B=/)) ||
                        (matches = rest.match(/^\u001B>/))
                    ){
                        i = i + matches[0].length - '\x1b'.length;
                        break;
                    }

                    if((i - text.length) < 10 && (rest.substring(1).search('\u001B') == -1)){
                        this.rest = rest;
                        i = text.length;
                    }

                    break;
                case '\n':
                    this.moveCursor(this.row + 1, 0);
                    break;
                default:
                    this.insertTextAtCursor(c);
                    this.moveCursor(this.row, this.col + 1);
                    break;
            }
        }
        this.updateHtml();
    }
}
