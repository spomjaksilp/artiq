from migen import *
from migen.genlib.io import DifferentialOutput, DifferentialInput, DDROutput


class SamplerPads(Module):
    def __init__(self, platform, eem0, eem1):
        self.sck_en = Signal()
        self.cnv = Signal()
        self.clkout = Signal()

        spip = platform.request("{}_adc_spi_p".format(eem0))
        spin = platform.request("{}_adc_spi_n".format(eem0))
        cnv = platform.request("{}_cnv".format(eem0))
        sdr = platform.request("{}_sdr".format(eem0))
        dp = platform.request("{}_adc_data_p".format(eem0))
        dn = platform.request("{}_adc_data_n".format(eem0))

        clkout_se = Signal()
        clkout_d = Signal()
        sck = Signal()

        self.specials += [
                DifferentialOutput(self.cnv, cnv.p, cnv.n),
                DifferentialOutput(1, sdr.p, sdr.n),
                DDROutput(0, self.sck_en, sck),
                DifferentialOutput(sck, spip.clk, spin.clk),
                DifferentialInput(dp.clkout, dn.clkout, clkout_se),
                Instance(
                    "IDELAYE2",
                    p_HIGH_PERFORMANCE_MODE="TRUE", p_IDELAY_TYPE="FIXED",
                    p_SIGNAL_PATTERN="CLOCK", p_IDELAY_VALUE=0,
                    p_REFCLK_FREQUENCY=200.,
                    i_IDATAIN=clkout_se, o_DATAOUT=clkout_d),
                Instance("BUFR", i_I=clkout_d, o_O=self.clkout)
        ]

        # here to be early before the input delays below to have the clock
        # available
        self.clkout_p = dp.clkout  # availabel for false paths
        platform.add_platform_command(
                "create_clock -name {clk} -period 8 [get_nets {clk}]",
                clk=dp.clkout)
        # platform.add_period_constraint(sampler_pads.clkout_p, 8.)
        for i in "abcd":
            sdo_se = Signal()
            sdo_d = Signal()
            sdo = Signal(2)
            setattr(self, "sdo{}".format(i), sdo)
            sdop = getattr(dp, "sdo{}".format(i))
            sdon = getattr(dn, "sdo{}".format(i))
            self.specials += [
                DifferentialInput(sdop, sdon, sdo_se),
                Instance(
                    "IDELAYE2",
                    p_HIGH_PERFORMANCE_MODE="TRUE", p_IDELAY_TYPE="FIXED",
                    p_SIGNAL_PATTERN="DATA", p_IDELAY_VALUE=31,
                    p_REFCLK_FREQUENCY=200.,
                    i_IDATAIN=sdo_se, o_DATAOUT=sdo_d),
                Instance("IDDR",
                    p_DDR_CLK_EDGE="SAME_EDGE",
                    i_C=~self.clkout, i_CE=1, i_S=0, i_R=0,
                    i_D=sdo_d, o_Q1=sdo[0], o_Q2=sdo[1])  # sdo[1] older
            ]
            # 4, -0+1.5 hold (t_HSDO_DDR), -0.2+0.2 skew
            platform.add_platform_command(
                "set_input_delay -clock {clk} "
                "-max 1.6 [get_ports {port}]\n"
                "set_input_delay -clock {clk} "
                "-min -0.1 [get_ports {port}]\n"
                "set_input_delay -clock {clk} "
                "-max 1.6 [get_ports {port}] -clock_fall -add_delay\n"
                "set_input_delay -clock {clk} "
                "-min -0.1 [get_ports {port}] -clock_fall -add_delay",
                clk=dp.clkout, port=sdop)


class UrukulPads(Module):
    def __init__(self, platform, eem00, eem01, eem10, eem11):
        spip, spin = [[
                platform.request("{}_qspi_{}".format(eem, pol), 0)
                for eem in (eem00, eem10)] for pol in "pn"]
        ioup = [platform.request("{}_io_update".format(eem), 0)
                for eem in (eem00, eem10)]
        self.cs_n = Signal()
        self.clk = Signal()
        self.io_update = Signal()
        self.specials += [(
                DifferentialOutput(self.cs_n, spip[i].cs_n, spin[i].cs_n),
                DifferentialOutput(self.clk, spip[i].clk, spin[i].clk),
                DifferentialOutput(self.io_update, ioup[i].p, ioup[i].n))
                for i in range(2)]
        for i in range(8):
            mosi = Signal()
            setattr(self, "mosi{}".format(i), mosi)
            self.specials += [
                DifferentialOutput(mosi,
                    getattr(spip[i // 4], "mosi{}".format(i % 4)),
                    getattr(spin[i // 4], "mosi{}".format(i % 4)))
            ]