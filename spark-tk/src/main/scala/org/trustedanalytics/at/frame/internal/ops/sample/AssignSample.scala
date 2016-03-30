package org.trustedanalytics.at.frame.internal.ops.sample

import org.apache.spark.org.trustedanalytics.at.frame.FrameRdd
import org.apache.spark.rdd.RDD
import org.apache.spark.sql.Row
import org.trustedanalytics.at.frame._
import org.trustedanalytics.at.frame.internal.{ BaseFrame, FrameState, FrameTransform }

trait AssignSampleTransform extends BaseFrame {

  def assignSample(samplePercentages: List[Double],
                   sampleLabels: Option[List[String]] = None,
                   outputColumn: Option[String] = None,
                   randomSeed: Option[Int] = None): Unit = {
    execute(AssignSample(samplePercentages, sampleLabels, outputColumn, randomSeed))
  }
}

/**
 * Randomly group rows into user-defined classes.
 *
 * @param samplePercentages Entries are non-negative and sum to 1. (See the note below.)
 *                          If the *i*'th entry of the  list is *p*, then then each row
 *                          receives label *i* with independent probability *p*.""")
 * @param sampleLabels Names to be used for the split classes. Defaults to "TR", "TE",
 *                     "VA" when the length of *sample_percentages* is 3, and defaults
 *                     to Sample_0, Sample_1, ... otherwise.
 * @param outputColumn Name of the new column which holds the labels generated by the
 *                     function
 * @param randomSeed Random seed used to generate the labels.  Defaults to 0.
 */
case class AssignSample(samplePercentages: List[Double],
                        sampleLabels: Option[List[String]] = None,
                        outputColumn: Option[String] = None,
                        randomSeed: Option[Int] = None) extends FrameTransform {

  def splitLabels: Array[String] = if (sampleLabels.isEmpty) {
    if (samplePercentages.length == 3) {
      Array("TR", "TE", "VA")
    }
    else {
      samplePercentages.indices.map(i => "Sample_" + i).toArray
    }
  }
  else {
    sampleLabels.get.toArray
  }

  override def work(state: FrameState): FrameState = {
    def sumOfPercentages = samplePercentages.sum
    def seed = randomSeed.getOrElse(0)
    def outputColumnName = outputColumn.getOrElse(state.schema.getNewColumnName("sample_bin"))

    // run the operation
    val splitter = new MLDataSplitter(samplePercentages.toArray, splitLabels, seed)
    val labeledRDD: RDD[LabeledLine[String, Row]] = splitter.randomlyLabelRDD(state.rdd)

    val splitRDD: RDD[Array[Any]] = labeledRDD.map((x: LabeledLine[String, Row]) =>
      (x.entry.toSeq :+ x.label.asInstanceOf[Any]).toArray[Any]
    )
    val updatedSchema = state.schema.addColumn(outputColumnName, DataTypes.string)
    FrameRdd.toFrameRdd(updatedSchema, splitRDD)
  }
}