#pragma once
void sim_scheduler_init(void);
void sim_scheduler_drain(void);
void sim_scheduler_advance(unsigned ms);
void sim_scheduler_destroy(void);
unsigned sim_scheduler_steps(void);
