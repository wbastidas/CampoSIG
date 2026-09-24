/**
 * Global test setup for the web suite.
 *
 * The only thing here is DOM cleanup, and it is here rather than repeated in each file because
 * forgetting it in one file produces "found multiple elements" in the *next* one — a failure
 * message that says nothing about what the test was checking.
 */

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(cleanup);
