// eslint-disable-next-line import/no-unresolved
import {
  html,
  css,
  LitElement,
} from 'https://cdn.jsdelivr.net/gh/lit/dist@2/core/lit-core.min.js';

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
    this.idservice = 'https://igsn-resolver.vercel.app/';
    this.identifier = '';
    this._canfollow = true;
    this._target = null;
    this._timeoutId = null;
  }

  get input() {
    return this.renderRoot?.querySelector('input#inp_identifier') ?? null;
  }

  async updateIdentifierInfo() {
    const idStr = this.identifier;
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
          window.console.log(_this._target);
          window.console.log(_this._canfollow);
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
      _this.updateIdentifierInfo();
    }, 250);
  }

  followIdentifier() {
    if (this._target !== null) {
      window.open(this._target, '_blank');
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
