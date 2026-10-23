import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AdminOverview, type ReportTrends } from './overview';

const trends: ReportTrends = {
  '7d': [{ label: 'Mon', lost: 2, found: 3 }],
  '30d': [{ label: 'Week 1', lost: 4, found: 5 }],
  '6m': [{ label: 'May', lost: 6, found: 7 }],
  '1y': [{ label: 'Jan', lost: 8, found: 9 }],
};

describe('AdminOverview', () => {
  it('renders the graph with an accessible name and changes its selected period', () => {
    render(<AdminOverview trends={trends}/>);

    expect(screen.getByRole('img', { name: 'Lost and found reports over 6 months' })).toBeTruthy();
    const weekButton = screen.getByRole('button', { name: '7 days' });
    expect(weekButton.getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(weekButton);

    expect(weekButton.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('img', { name: 'Lost and found reports over 7 days' })).toBeTruthy();
  });
});
