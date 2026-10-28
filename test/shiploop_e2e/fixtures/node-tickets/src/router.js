'use strict';

const { InvalidError } = require('./errors');

/**
 * A small router. A route is a method and a path pattern; a `:name` segment matches one path segment, which reaches
 * the handler decoded, in `params`. Routes are tried in the order they were added, and a trailing slash is ignored.
 */
class Router {
  constructor() {
    this.routes = [];
  }

  add(method, pattern, handler) {
    const names = [];
    const source = pattern
      .split('/')
      .map((segment) => {
        if (!segment.startsWith(':')) return segment.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        names.push(segment.slice(1));
        return '([^/]+)';
      })
      .join('/');
    this.routes.push({ method, pattern, names, handler, regex: new RegExp(`^${source}/?$`) });
    return this;
  }

  get(pattern, handler) {
    return this.add('GET', pattern, handler);
  }

  post(pattern, handler) {
    return this.add('POST', pattern, handler);
  }

  put(pattern, handler) {
    return this.add('PUT', pattern, handler);
  }

  patch(pattern, handler) {
    return this.add('PATCH', pattern, handler);
  }

  delete(pattern, handler) {
    return this.add('DELETE', pattern, handler);
  }

  /** The route for `method` and `pathname`: { handler, params, pattern }, or null when no route matches. */
  match(method, pathname) {
    for (const route of this.routes) {
      if (route.method !== method) continue;
      const found = route.regex.exec(pathname);
      if (!found) continue;
      const params = {};
      route.names.forEach((name, index) => {
        params[name] = decode(found[index + 1]);
      });
      return { handler: route.handler, params, pattern: route.pattern };
    }
    return null;
  }

  /** The methods some route answers for `pathname`: for the message of a request whose method is wrong. */
  methodsFor(pathname) {
    const methods = this.routes.filter((route) => route.regex.test(pathname)).map((route) => route.method);
    return [...new Set(methods)];
  }
}

function decode(segment) {
  try {
    return decodeURIComponent(segment);
  } catch {
    throw new InvalidError(`path segment ${segment} is not valid percent-encoding`);
  }
}

module.exports = { Router };
