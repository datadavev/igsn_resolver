import { html, css, LitElement } from 'https://unpkg.com/lit-html?module';

export class IdentifierResolver extends LitElement {
  static get styles() {
    return css`
      :host {
        display: block;
        padding: 25px;
        color: var(--identifier-resolver-text-color, #000);
      }
    `;
  }

  static get properties() {
    return {
      idservice: { type: String },
      identifier: { type: String },
      counter: { type: Number },
    };
  }

  constructor() {
    super();
    this.idservice = 'https://ule1dz.deta.dev/';
    this.identifier = '';
    this._canfollow = true;
    this._target = null;
    this._timeoutId = null;
  }

  get input() {
    return this.renderRoot?.querySelector('input#inp_identifier') ?? null;
  }

  async updateIdentifierInfo(idStr) {
    const ele = this.renderRoot?.querySelector('pre#id_info') ?? null;
    ele.innerText = 'Loading...';
    const _this = this;
    if (idStr.length > 3) {
      const url = `${this.idservice}.info/${idStr}`;
      fetch(url)
        .then(response => response.json())
        .then(data => {
          try {
            _this._target = data[0].target ?? null;
          } catch (err) {
            _this._target = null;
          }
          _this._canfollow = _this._target !== null;
          console.log(_this._target);
          console.log(_this._canfollow);
          ele.innerText = JSON.stringify(data[0], null, 2);
        });
    } else {
      ele.innerText = '';
    }
  }

  updateIdentifier() {
    this.identifier = this.input.value;
    clearTimeout(this._timeoutId);
    const _this = this;
    this._timeoutId = setTimeout(() => {
      _this.updateIdentifierInfo(this.identifier);
    }, 250);
  }

  followIdentifier() {
    if (this._target !== null) {
      window.location.href = this._target;
    }
  }

  render() {
    return html`
      <input
        id="inp_identifier"
        type="text"
        .value=${this.identifier}
        placeholder="AU1243"
        @keyup=${this.updateIdentifier}
        size="50"
        title="Enter an IGSN or DOI identifier"
      />
      <input
        type="button"
        value="↗⧉"
        @click=${this.followIdentifier}
        title="Click to follow target address."
      />
      <pre id="id_info" title="Information about identifier"></pre>
    `;
  }
}
